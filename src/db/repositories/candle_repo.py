"""Candle veritabanı operasyonları."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.candle import Candle
from src.schemas.candle import CandleCreate


class CandleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, candle: CandleCreate) -> None:
        """Candle ekle veya mevcutsa güncelle (conflict on unique key)."""
        stmt = pg_insert(Candle).values(**candle.model_dump())
        stmt = stmt.on_conflict_do_update(
            constraint="uq_candles_symbol_interval_time",
            set_={
                "close": stmt.excluded.close,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "volume": stmt.excluded.volume,
                "quote_volume": stmt.excluded.quote_volume,
                "trade_count": stmt.excluded.trade_count,
            },
        )
        await self.session.execute(stmt)

    async def upsert_many(self, candles: list[CandleCreate]) -> int:
        """Toplu candle ekle/güncelle."""
        if not candles:
            return 0
        for candle in candles:
            await self.upsert(candle)
        return len(candles)

    async def get_recent(
        self,
        symbol: str,
        interval: str,
        limit: int = 200,
    ) -> list[Candle]:
        """En son N candle'ı getir (eskiden yeniye sıralı)."""
        stmt = (
            sa.select(Candle)
            .where(Candle.symbol == symbol, Candle.interval == interval)
            .order_by(Candle.open_time.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        candles = list(result.scalars().all())
        candles.reverse()  # Eskiden yeniye
        return candles

    async def get_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[Candle]:
        """Belirli zaman aralığındaki candle'ları getir (limit korumalı)."""
        stmt = (
            sa.select(Candle)
            .where(
                Candle.symbol == symbol,
                Candle.interval == interval,
                Candle.open_time >= start,
                Candle.open_time <= end,
            )
            .order_by(Candle.open_time.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest(self, symbol: str, interval: str) -> Candle | None:
        """En son candle'ı getir."""
        stmt = (
            sa.select(Candle)
            .where(Candle.symbol == symbol, Candle.interval == interval)
            .order_by(Candle.open_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self, symbol: str, interval: str) -> int:
        """Candle sayısını getir."""
        stmt = (
            sa.select(sa.func.count())
            .select_from(Candle)
            .where(Candle.symbol == symbol, Candle.interval == interval)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
