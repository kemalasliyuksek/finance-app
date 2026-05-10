"""Audit log helper — işlem kayıt fonksiyonu."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.audit_log import AuditLog

logger = get_logger("audit")


async def log_audit(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    user: str = "system",
    changes: dict | None = None,
    details: str | None = None,
) -> None:
    """Audit log kaydı oluştur.

    Args:
        session: Aktif DB session (mevcut transaction içinde kullanılır)
        action: İşlem tipi (create, update, delete, approve, reject)
        entity_type: Varlık tipi (signal, order, trade, config, user)
        entity_id: Varlık ID'si
        user: İşlemi yapan kullanıcı
        changes: Değişiklik detayları (JSON)
        details: Ek açıklama
    """
    audit = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        changes=changes,
        details=details,
    )
    session.add(audit)
    await session.flush()

    logger.info(
        "audit_logged",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
    )
