from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.payment import PaymentAccepted, PaymentCreate, PaymentRead
from app.services.payments import (
    IdempotencyConflictError,
    create_payment,
    get_payment,
)


router = APIRouter(prefix="/payments", tags=["payments"])
Session = Annotated[AsyncSession, Depends(get_session)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=255),
]


@router.post(
    "",
    response_model=PaymentAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_payment_endpoint(
    body: PaymentCreate,
    session: Session,
    idempotency_key: IdempotencyKey,
) -> PaymentAccepted:
    try:
        payment = await create_payment(session, body, idempotency_key)
    except IdempotencyConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with another request",
        ) from None
    return PaymentAccepted(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment_endpoint(
    payment_id: UUID,
    session: Session,
) -> PaymentRead:
    payment = await get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return PaymentRead.model_validate(payment)
