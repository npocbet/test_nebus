from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import PaymentStatus
from app.models.outbox import Outbox
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate


class IdempotencyConflictError(Exception):
    """The same idempotency key was reused for a different request."""


def _matches_request(payment: Payment, data: PaymentCreate) -> bool:
    return (
        payment.amount == data.amount
        and payment.currency == data.currency
        and payment.description == data.description
        and payment.metadata_ == data.metadata
        and payment.webhook_url == str(data.webhook_url)
    )


async def create_payment(
    session: AsyncSession,
    data: PaymentCreate,
    idempotency_key: str,
) -> Payment:
    payment = Payment(
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        metadata_=data.metadata,
        status=PaymentStatus.PENDING,
        idempotency_key=idempotency_key,
        webhook_url=str(data.webhook_url),
    )

    try:
        async with session.begin():
            session.add(payment)
            await session.flush()

            session.add(
                Outbox(
                    event_type="payment.created",
                    aggregate_id=payment.id,
                    payload={
                        "payment_id": str(payment.id),
                        "amount": str(payment.amount),
                        "currency": payment.currency.value,
                        "webhook_url": payment.webhook_url,
                    },
                )
            )
    except IntegrityError:
        # A concurrent or repeated request may use the same idempotency key.
        # The unique DB constraint is the final guard against duplicates.
        await session.rollback()
        existing = await session.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise
        if not _matches_request(existing, data):
            raise IdempotencyConflictError from None
        return existing

    return payment


async def get_payment(session: AsyncSession, payment_id: UUID) -> Payment | None:
    return await session.get(Payment, payment_id)
