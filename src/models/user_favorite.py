"""Kullanıcı favori coinleri modeli."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class UserFavorite(Base, TimestampMixin):
    __tablename__ = "user_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_favorites_user_symbol"),
        Index("ix_user_favorites_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trading.users.id"), nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
