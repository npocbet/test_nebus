from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import OutboxStatus


class OutboxEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1, max_length=100)
    aggregate_id: UUID
    payload: dict[str, Any]


class OutboxEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    aggregate_id: UUID
    payload: dict[str, Any]
    status: OutboxStatus
    attempts: int = Field(ge=0)
    next_attempt_at: datetime | None
    created_at: datetime
    published_at: datetime | None
