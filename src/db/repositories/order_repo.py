"""Order veritabanı operasyonları."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import OrderStatus
from src.models.order import Order
from src.schemas.order import OrderCreate


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, order: OrderCreate, client_oid: str | None = None) -> Order:
        """Yeni emir oluştur."""
        db_order = Order(
            **order.model_dump(),
            binance_client_oid=client_oid,
        )
        self.session.add(db_order)
        await self.session.flush()
        return db_order

    async def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        return await self.session.get(Order, order_id)

    async def get_by_client_oid(self, client_oid: str) -> Order | None:
        """Binance client order ID ile emir getir (idempotency)."""
        stmt = sa.select(Order).where(Order.binance_client_oid == client_oid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_fill(
        self,
        order_id: uuid.UUID,
        *,
        binance_order_id: int | None = None,
        status: OrderStatus,
        filled_quantity: float | None = None,
        avg_fill_price: float | None = None,
        commission: float | None = None,
        commission_asset: str | None = None,
    ) -> None:
        """Emir fill bilgisini güncelle."""
        values: dict = {"status": status}
        if binance_order_id is not None:
            values["binance_order_id"] = binance_order_id
        if filled_quantity is not None:
            values["filled_quantity"] = filled_quantity
        if avg_fill_price is not None:
            values["avg_fill_price"] = avg_fill_price
        if commission is not None:
            values["commission"] = commission
        if commission_asset is not None:
            values["commission_asset"] = commission_asset

        stmt = sa.update(Order).where(Order.id == order_id).values(**values)
        await self.session.execute(stmt)

    async def get_open_orders(self, symbol: str | None = None) -> list[Order]:
        """Açık emirleri getir."""
        conditions = [Order.status.in_([OrderStatus.NEW, OrderStatus.SUBMITTED]), Order.deleted_at.is_(None)]
        if symbol:
            conditions.append(Order.symbol == symbol)
        stmt = (
            sa.select(Order)
            .where(*conditions)
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    _sortable_columns = {
        "created_at": Order.created_at,
        "symbol": Order.symbol,
        "side": Order.side,
        "status": Order.status,
        "quantity": Order.quantity,
    }

    async def get_filtered(
        self,
        *,
        status: OrderStatus | None = None,
        symbol: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[Order], int]:
        """Filtrelenmiş ve sayfalanmış emir listesi."""
        conditions = [Order.deleted_at.is_(None)]
        if status:
            conditions.append(Order.status == status)
        if symbol:
            conditions.append(Order.symbol == symbol.upper())

        count_stmt = sa.select(sa.func.count()).select_from(Order)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        order_col = self._sortable_columns.get(sort_by, Order.created_at)
        order_clause = order_col.asc() if sort_order == "asc" else order_col.desc()

        query = sa.select(Order).order_by(order_clause).limit(limit).offset(offset)
        if conditions:
            query = query.where(*conditions)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
