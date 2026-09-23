from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel

from app.domain.enums import Currency, PaymentStatus


class PaymentCreatedMessage(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: Currency
    webhook_url: AnyHttpUrl


class PaymentWebhook(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    metadata: dict[str, Any]
    processed_at: datetime
