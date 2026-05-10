"""Emir şemaları."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from src.constants import OrderStatus, OrderType, Side


class OrderCreate(BaseModel):
    signal_id: uuid.UUID | None = None
    symbol: str
    side: Side
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None


class OrderRead(BaseModel):
    id: uuid.UUID
    signal_id: uuid.UUID | None
    binance_order_id: int | None
    binance_client_oid: str | None
    symbol: str
    side: Side
    order_type: str
    quantity: Decimal
    price: Decimal | None
    stop_price: Decimal | None
    status: OrderStatus
    filled_quantity: Decimal
    avg_fill_price: Decimal | None
    commission: Decimal
    commission_asset: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
