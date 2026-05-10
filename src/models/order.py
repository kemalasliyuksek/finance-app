"""Emir (order) modeli."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, SoftDeleteMixin, TimestampMixin


class Order(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_signal", "signal_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_binance", "binance_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trading.signals.id")
    )
    binance_order_id: Mapped[int | None] = mapped_column(BigInteger)
    binance_client_oid: Mapped[str | None] = mapped_column(String(36), unique=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    filled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, default=Decimal("0")
    )
    avg_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    commission: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, default=Decimal("0")
    )
    commission_asset: Mapped[str | None] = mapped_column(String(10))
    error_message: Mapped[str | None] = mapped_column(Text)

    # İlişkiler
    signal = relationship("Signal", backref="orders", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<Order {self.id!s:.8} {self.symbol} {self.side} "
            f"{self.order_type} qty={self.quantity} status={self.status}>"
        )
