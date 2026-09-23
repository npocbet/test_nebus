import asyncio
import contextlib
import logging
import random
from datetime import UTC, datetime

import httpx
from faststream import FastStream
from sqlalchemy import update

from app.db.session import async_session_factory
from app.domain.enums import PaymentStatus
from app.messaging.broker import PAYMENTS_QUEUE, broker
from app.messaging.outbox import publish_outbox_forever
from app.models.payment import Payment
from app.schemas.messages import PaymentCreatedMessage, PaymentWebhook


logger = logging.getLogger(__name__)
app = FastStream(broker)
_outbox_task: asyncio.Task[None] | None = None


async def _send_webhook(payment: Payment) -> None:
    payload = PaymentWebhook(
        payment_id=payment.id,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        metadata=payment.metadata_,
        processed_at=payment.processed_at,
    )

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            payment.webhook_url,
            json=payload.model_dump(mode="json"),
            headers={"Idempotency-Key": str(payment.id)},
        )
        response.raise_for_status()


async def _process_payment_once(message: PaymentCreatedMessage) -> None:
    async with async_session_factory() as session:
        payment = await session.get(Payment, message.payment_id)
        if payment is None:
            raise LookupError(f"Payment {message.payment_id} does not exist")
        if payment.webhook_delivered_at is not None:
            return
        is_pending = payment.status == PaymentStatus.PENDING

    if is_pending:
        # Gateway latency must not occupy a DB connection or hold a row lock.
        await asyncio.sleep(random.uniform(2, 5))
        result = (
            PaymentStatus.SUCCEEDED
            if random.random() < 0.9
            else PaymentStatus.FAILED
        )
        async with async_session_factory.begin() as session:
            await session.execute(
                update(Payment)
                .where(
                    Payment.id == message.payment_id,
                    Payment.status == PaymentStatus.PENDING,
                )
                .values(status=result, processed_at=datetime.now(UTC))
            )

    # Reload the committed winner without retaining a DB connection during HTTP.
    async with async_session_factory() as session:
        payment = await session.get(Payment, message.payment_id)
        if payment is None:
            raise LookupError(f"Payment {message.payment_id} does not exist")
        if payment.webhook_delivered_at is not None:
            return
        session.expunge(payment)

    await _send_webhook(payment)

    async with async_session_factory.begin() as session:
        await session.execute(
            update(Payment)
            .where(
                Payment.id == message.payment_id,
                Payment.webhook_delivered_at.is_(None),
            )
            .values(webhook_delivered_at=datetime.now(UTC))
        )


@broker.subscriber(PAYMENTS_QUEUE)
async def process_payment(message: PaymentCreatedMessage) -> None:
    for attempt in range(1, 4):
        try:
            await _process_payment_once(message)
            return
        except Exception:
            if attempt == 3:
                logger.exception(
                    "Payment %s failed after 3 attempts; rejecting to DLQ",
                    message.payment_id,
                )
                raise

            delay = 2 ** (attempt - 1)
            logger.warning(
                "Payment %s attempt %s failed; retrying in %s seconds",
                message.payment_id,
                attempt,
                delay,
                exc_info=True,
            )
            await asyncio.sleep(delay)


@app.on_startup
async def start_outbox_publisher() -> None:
    global _outbox_task
    _outbox_task = asyncio.create_task(publish_outbox_forever())


@app.on_shutdown
async def stop_outbox_publisher() -> None:
    if _outbox_task is None:
        return
    _outbox_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _outbox_task
