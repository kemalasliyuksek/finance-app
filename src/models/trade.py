"""Trade (pozisyon) modeli - açık ve kapalı işlemler."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, SoftDeleteMixin, TimestampMixin


class Trade(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_status", "status", "opened_at"),
        Index("ix_trades_symbol", "symbol", "opened_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trading.orders.id")
    )
    exit_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trading.orders.id")
    )
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    realized_pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    total_commission: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column()
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    # İlişkiler
    entry_order = relationship("Order", foreign_keys=[entry_order_id], lazy="selectin")
    exit_order = relationship("Order", foreign_keys=[exit_order_id], lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<Trade {self.id!s:.8} {self.symbol} {self.side} "
            f"entry={self.entry_price} status={self.status}>"
        )
