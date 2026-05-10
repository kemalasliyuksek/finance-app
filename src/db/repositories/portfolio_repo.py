"""Portfolio snapshot veritabanı operasyonları."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.portfolio_snapshot import PortfolioSnapshot


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_snapshot(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_latest(self) -> PortfolioSnapshot | None:
        stmt = (
            sa.select(PortfolioSnapshot)
            .order_by(PortfolioSnapshot.snapshot_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_range(
        self, start: datetime, end: datetime
    ) -> list[PortfolioSnapshot]:
        stmt = (
            sa.select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.snapshot_at >= start,
                PortfolioSnapshot.snapshot_at <= end,
            )
            .order_by(PortfolioSnapshot.snapshot_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
