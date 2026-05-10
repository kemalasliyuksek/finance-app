"""Trade veritabanı operasyonları."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import TradeStatus
from src.models.trade import Trade


class TradeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, trade: Trade) -> Trade:
        self.session.add(trade)
        await self.session.flush()
        return trade

    async def get_by_id(self, trade_id: uuid.UUID) -> Trade | None:
        return await self.session.get(Trade, trade_id)

    async def get_open_trades(self, symbol: str | None = None) -> list[Trade]:
        """Açık pozisyonları getir."""
        conditions = [Trade.status == TradeStatus.OPEN, Trade.deleted_at.is_(None)]
        if symbol:
            conditions.append(Trade.symbol == symbol)
        stmt = (
            sa.select(Trade).where(*conditions).order_by(Trade.opened_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def close_trade(
        self,
        trade_id: uuid.UUID,
        *,
        exit_order_id: uuid.UUID | None,
        exit_price: float,
        realized_pnl: float,
        realized_pnl_pct: float,
        total_commission: float,
    ) -> None:
        """Trade'i kapat."""
        # opened_at/closed_at DB'de naive timestamp — tutarlılık için naive kullan
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        trade = await self.get_by_id(trade_id)
        if not trade:
            return

        # Timezone-safe süre hesabı
        opened = trade.opened_at
        if opened:
            if opened.tzinfo:
                opened = opened.replace(tzinfo=None)
            duration = int((now - opened).total_seconds())
        else:
            duration = None

        stmt = (
            sa.update(Trade)
            .where(Trade.id == trade_id)
            .values(
                exit_order_id=exit_order_id,
                exit_price=exit_price,
                realized_pnl=realized_pnl,
                realized_pnl_pct=realized_pnl_pct,
                total_commission=total_commission,
                status=TradeStatus.CLOSED,
                closed_at=now,
                duration_seconds=duration,
            )
        )
        await self.session.execute(stmt)

    async def get_today_trades(self) -> list[Trade]:
        """Bugünkü trade'leri getir."""
        # opened_at kolonu DB'de naive timestamp — tzinfo kaldırılmalı
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None,
        )
        stmt = (
            sa.select(Trade)
            .where(Trade.opened_at >= today_start, Trade.deleted_at.is_(None))
            .order_by(Trade.opened_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_closed_trades(self, limit: int = 50) -> list[Trade]:
        """Kapanmış trade'leri getir."""
        stmt = (
            sa.select(Trade)
            .where(Trade.status == TradeStatus.CLOSED, Trade.deleted_at.is_(None))
            .order_by(Trade.closed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_open(self) -> int:
        """Açık pozisyon sayısı."""
        stmt = (
            sa.select(sa.func.count())
            .select_from(Trade)
            .where(Trade.status == TradeStatus.OPEN, Trade.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    _sortable_columns = {
        "opened_at": Trade.opened_at,
        "symbol": Trade.symbol,
        "realized_pnl": Trade.realized_pnl,
        "realized_pnl_pct": Trade.realized_pnl_pct,
        "status": Trade.status,
    }

    async def get_filtered(
        self,
        *,
        status: TradeStatus | None = None,
        symbol: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[Trade], int]:
        """Filtrelenmiş ve sayfalanmış trade listesi."""
        conditions = [Trade.deleted_at.is_(None)]
        if status:
            conditions.append(Trade.status == status)
        if symbol:
            conditions.append(Trade.symbol == symbol.upper())

        count_stmt = sa.select(sa.func.count()).select_from(Trade)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        order_col = self._sortable_columns.get(sort_by, Trade.opened_at)
        order_clause = order_col.asc() if sort_order == "asc" else order_col.desc()

        query = sa.select(Trade).order_by(order_clause).limit(limit).offset(offset)
        if conditions:
            query = query.where(*conditions)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def get_stats(self) -> dict:
        """Trade istatistikleri — SQL aggregation ile tek sorguda."""
        from decimal import Decimal
        from sqlalchemy import case, func

        stmt = (
            sa.select(
                func.count().label("total"),
                func.coalesce(func.sum(Trade.realized_pnl), 0).label("total_pnl"),
                func.sum(case((Trade.realized_pnl > 0, 1), else_=0)).label("winning"),
                func.sum(case((Trade.realized_pnl < 0, 1), else_=0)).label("losing"),
                func.coalesce(func.max(Trade.realized_pnl), 0).label("best"),
                func.coalesce(func.min(Trade.realized_pnl), 0).label("worst"),
            )
            .where(Trade.status == TradeStatus.CLOSED, Trade.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        row = result.one()

        total = row.total or 0
        winning = row.winning or 0
        total_pnl = Decimal(str(row.total_pnl or 0))
        best = Decimal(str(row.best or 0))
        worst = Decimal(str(row.worst or 0))

        return {
            "total_trades": total,
            "winning_trades": winning,
            "losing_trades": row.losing or 0,
            "win_rate": Decimal(winning) / Decimal(total) if total else Decimal("0"),
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / Decimal(total) if total else Decimal("0"),
            "best_trade_pnl": best,
            "worst_trade_pnl": worst,
        }
