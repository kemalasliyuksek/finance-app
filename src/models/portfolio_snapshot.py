"""Portföy anlık görüntüsü modeli."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Index, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (Index("ix_snapshots_time", "snapshot_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    total_balance_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    free_balance_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    locked_balance_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, default=Decimal("0")
    )
    open_positions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    asset_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    def __repr__(self) -> str:
        return (
            f"<PortfolioSnapshot {self.snapshot_at} "
            f"balance={self.total_balance_usdt} USDT>"
        )
