"""Sinyal şemaları."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from src.constants import Side, SignalStatus


class SignalCreate(BaseModel):
    symbol: str
    side: Side
    strategy: str
    confidence: Decimal
    entry_price: Decimal

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 1:
            raise ValueError(f"confidence must be between 0 and 1, got {v}")
        return v
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    indicators: dict
    sentiment_score: Decimal | None = None
    expires_at: datetime


class SignalRead(BaseModel):
    id: uuid.UUID
    symbol: str
    side: Side
    strategy: str
    confidence: Decimal
    entry_price: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    indicators: dict
    sentiment_score: Decimal | None
    status: SignalStatus
    approved_at: datetime | None
    approved_by: str | None
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class SignalApproval(BaseModel):
    approved: bool
    approved_by: str = "user_telegram"


class TimelineEvent(BaseModel):
    action: str
    timestamp: datetime
    user: str | None = None
    details: dict | None = None


class SignalDetailRead(BaseModel):
    signal: SignalRead
    order: dict | None = None
    trade: dict | None = None
    timeline: list[TimelineEvent] = []
