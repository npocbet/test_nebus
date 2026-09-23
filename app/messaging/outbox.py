import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select

from app.db.session import async_session_factory
from app.domain.enums import OutboxStatus
from app.messaging.broker import payment_publisher
from app.models.outbox import Outbox


logger = logging.getLogger(__name__)
POLL_INTERVAL_SECONDS = 1
PUBLISH_BATCH_SIZE = 100


async def publish_outbox_forever() -> None:
    while True:
        try:
            published = await _publish_batch()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected outbox publisher error")
            published = 0

        if published == 0:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _publish_batch() -> int:
    now = datetime.now(UTC)
    async with async_session_factory() as session:
        async with session.begin():
            events = list(
                await session.scalars(
                    select(Outbox)
                    .where(
                        Outbox.status == OutboxStatus.PENDING,
                        or_(
                            Outbox.next_attempt_at.is_(None),
                            Outbox.next_attempt_at <= now,
                        ),
                    )
                    .order_by(Outbox.created_at)
                    .limit(PUBLISH_BATCH_SIZE)
                    .with_for_update(skip_locked=True)
                )
            )

            for event in events:
                try:
                    await payment_publisher.publish(
                        event.payload,
                        message_id=str(event.id),
                    )
                except Exception:
                    event.attempts += 1
                    delay = min(2 ** (event.attempts - 1), 60)
                    event.next_attempt_at = now + timedelta(seconds=delay)
                    logger.exception("Could not publish outbox event %s", event.id)
                else:
                    event.status = OutboxStatus.PUBLISHED
                    event.published_at = now
                    event.next_attempt_at = None

    return len(events)
