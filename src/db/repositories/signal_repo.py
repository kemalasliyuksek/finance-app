"""Signal veritabanı operasyonları."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import SignalStatus
from src.models.order import Order
from src.models.signal import Signal
from src.schemas.signal import SignalCreate


class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, signal: SignalCreate) -> Signal:
        """Yeni sinyal oluştur."""
        db_signal = Signal(**signal.model_dump())
        self.session.add(db_signal)
        await self.session.flush()
        return db_signal

    async def get_by_id(self, signal_id: uuid.UUID) -> Signal | None:
        """ID ile sinyal getir."""
        return await self.session.get(Signal, signal_id)

    async def update_status(
        self,
        signal_id: uuid.UUID,
        status: SignalStatus,
        approved_by: str | None = None,
        expected_status: SignalStatus | None = None,
    ) -> bool:
        """Sinyal durumunu güncelle.

        Args:
            expected_status: Belirtilirse, sadece mevcut durum bu ise günceller (atomik).
                            Race condition önlemi.

        Returns:
            True güncelleme başarılı, False durum değişmiş (concurrent update).
        """
        values: dict = {"status": status}
        if status == SignalStatus.APPROVED:
            values["approved_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
            values["approved_by"] = approved_by or "auto"

        conditions = [Signal.id == signal_id]
        if expected_status is not None:
            conditions.append(Signal.status == expected_status)

        stmt = sa.update(Signal).where(*conditions).values(**values)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_pending(self, limit: int = 20) -> list[Signal]:
        """Bekleyen sinyalleri getir."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            sa.select(Signal)
            .where(Signal.status == SignalStatus.PENDING, Signal.expires_at > now, Signal.deleted_at.is_(None))
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def expire_old_signals(self) -> int:
        """Süresi dolmuş sinyalleri expired olarak işaretle."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            sa.update(Signal)
            .where(Signal.status == SignalStatus.PENDING, Signal.expires_at <= now)
            .values(status=SignalStatus.EXPIRED)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_recent(self, limit: int = 20) -> list[Signal]:
        """En son sinyalleri getir."""
        stmt = (
            sa.select(Signal)
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # Sıralama için izin verilen kolon adları
    _sortable_columns = {
        "created_at": Signal.created_at,
        "symbol": Signal.symbol,
        "side": Signal.side,
        "confidence": Signal.confidence,
        "status": Signal.status,
    }

    async def get_filtered(
        self,
        *,
        status: SignalStatus | None = None,
        symbol: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[Signal], int]:
        """Filtrelenmiş ve sayfalanmış sinyal listesi."""
        conditions = [Signal.deleted_at.is_(None)]
        if status:
            conditions.append(Signal.status == status)
        if symbol:
            conditions.append(Signal.symbol == symbol.upper())

        count_stmt = sa.select(sa.func.count()).select_from(Signal)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Dinamik sıralama
        order_col = self._sortable_columns.get(sort_by, Signal.created_at)
        order_clause = order_col.asc() if sort_order == "asc" else order_col.desc()

        query = sa.select(Signal).order_by(order_clause).limit(limit).offset(offset)
        if conditions:
            query = query.where(*conditions)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def get_approved_without_orders(self) -> list[Signal]:
        """Approved ama order'ı olmayan sinyalleri getir (startup recovery için)."""
        stmt = (
            sa.select(Signal)
            .outerjoin(Order, Order.signal_id == Signal.id)
            .where(Signal.status == SignalStatus.APPROVED)
            .where(Order.id.is_(None))
            .where(Signal.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
