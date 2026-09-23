from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.enums import Currency
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.services.payments import _matches_request


def payment_data(**overrides) -> PaymentCreate:
    values = {
        "amount": "1500.00",
        "currency": "RUB",
        "description": "Order 123",
        "metadata": {"order_id": "123"},
        "webhook_url": "https://example.com/payment-webhook",
    }
    values.update(overrides)
    return PaymentCreate.model_validate(values)


def stored_payment(data: PaymentCreate) -> Payment:
    return Payment(
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        metadata_=data.metadata,
        idempotency_key="order-123",
        webhook_url=str(data.webhook_url),
    )


def test_same_idempotent_request_matches() -> None:
    data = payment_data()
    assert _matches_request(stored_payment(data), data)


@pytest.mark.parametrize(
    "changed",
    [
        {"amount": "1501.00"},
        {"currency": "USD"},
        {"description": "Another order"},
        {"metadata": {"order_id": "456"}},
        {"webhook_url": "https://example.org/hook"},
    ],
)
def test_changed_idempotent_request_does_not_match(changed: dict) -> None:
    original = payment_data()
    assert not _matches_request(stored_payment(original), payment_data(**changed))


def test_payment_rejects_non_positive_amount() -> None:
    with pytest.raises(ValidationError):
        payment_data(amount="0")


def test_payment_accepts_supported_currency() -> None:
    assert payment_data(currency="EUR").currency is Currency.EUR


def test_decimal_keeps_two_fraction_digits() -> None:
    assert payment_data().amount == Decimal("1500.00")
