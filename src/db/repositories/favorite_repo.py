"""Kullanıcı favori coin operasyonları."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user_favorite import UserFavorite


class FavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_symbols_by_user(self, user_id: uuid.UUID) -> list[str]:
        stmt = (
            sa.select(UserFavorite.symbol)
            .where(UserFavorite.user_id == user_id)
            .order_by(UserFavorite.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, user_id: uuid.UUID, symbol: str) -> UserFavorite | None:
        fav = UserFavorite(user_id=user_id, symbol=symbol)
        self.session.add(fav)
        try:
            await self.session.flush()
            return fav
        except IntegrityError:
            await self.session.rollback()
            return None

    async def remove(self, user_id: uuid.UUID, symbol: str) -> bool:
        stmt = sa.delete(UserFavorite).where(
            UserFavorite.user_id == user_id,
            UserFavorite.symbol == symbol,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
