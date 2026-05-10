"""Kullanıcı modeli."""

from __future__ import annotations

import uuid

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(20), default="admin")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
