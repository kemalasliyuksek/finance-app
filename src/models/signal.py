"""Trading sinyal modeli."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, SoftDeleteMixin, TimestampMixin


class Signal(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_status", "status", "created_at"),
        Index("ix_signals_symbol", "symbol", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY / SELL
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    indicators: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    approved_at: Mapped[datetime | None] = mapped_column()
    approved_by: Mapped[str | None] = mapped_column(String(50))
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return (
            f"<Signal {self.id!s:.8} {self.symbol} {self.side} "
            f"conf={self.confidence} status={self.status}>"
        )
