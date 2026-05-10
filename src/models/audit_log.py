"""Audit log modeli — kim, ne zaman, ne değiştirdi."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create/update/delete
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # signal/order/trade/config
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False)
    user: Mapped[str] = mapped_column(String(50), nullable=False)  # dashboard/telegram/system
    changes: Mapped[dict | None] = mapped_column(JSONB)
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
