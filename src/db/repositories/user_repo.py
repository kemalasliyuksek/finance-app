"""Kullanıcı veritabanı operasyonları."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> User | None:
        stmt = sa.select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        username: str,
        password_hash: str,
        role: str = "admin",
        must_change_password: bool = False,
    ) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            role=role,
            must_change_password=must_change_password,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def count(self) -> int:
        stmt = sa.select(sa.func.count()).select_from(User)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_password(self, username: str, password_hash: str) -> None:
        stmt = (
            sa.update(User)
            .where(User.username == username)
            .values(password_hash=password_hash)
        )
        await self.session.execute(stmt)

    async def update_must_change_password(self, username: str, value: bool) -> None:
        stmt = (
            sa.update(User)
            .where(User.username == username)
            .values(must_change_password=value)
        )
        await self.session.execute(stmt)
