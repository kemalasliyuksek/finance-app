"""Sinyal onay/red handler - Telegram inline keyboard callback'leri yönetir."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.constants import SignalStatus
from src.core.events import publish
from src.core.logging import get_logger
from src.db.repositories.signal_repo import SignalRepository
from src.db.session import get_session

logger = get_logger("approval_handler")

# Callback data format: "approve:{signal_id}" veya "reject:{signal_id}"
CALLBACK_APPROVE = "approve"
CALLBACK_REJECT = "reject"


async def handle_approval(signal_id_str: str, approved: bool, user: str = "telegram") -> dict:
    """Sinyal onay/red islemini yap.

    Args:
        signal_id_str: Signal UUID string
        approved: True=onayla, False=reddet
        user: Onaylayan kullanici

    Returns:
        {"success": bool, "message": str, "signal_id": str}
    """
    try:
        signal_id = uuid.UUID(signal_id_str)
    except ValueError:
        return {"success": False, "message": "Geçersiz sinyal ID", "signal_id": signal_id_str}

    async with get_session() as session:
        repo = SignalRepository(session)
        signal = await repo.get_by_id(signal_id)

        if not signal:
            return {"success": False, "message": "Sinyal bulunamadı", "signal_id": signal_id_str}

        if signal.status != SignalStatus.PENDING:
            return {
                "success": False,
                "message": f"Sinyal zaten işlendi: {signal.status}",
                "signal_id": signal_id_str,
            }

        # Süre kontrolü
        expires = signal.expires_at.replace(tzinfo=None) if signal.expires_at.tzinfo else signal.expires_at
        if expires < datetime.utcnow():
            await repo.update_status(signal_id, SignalStatus.EXPIRED, expected_status=SignalStatus.PENDING)
            return {
                "success": False,
                "message": "Sinyal süresi dolmuş",
                "signal_id": signal_id_str,
            }

        if approved:
            updated = await repo.update_status(signal_id, SignalStatus.APPROVED, approved_by=user, expected_status=SignalStatus.PENDING)
            if not updated:
                return {"success": False, "message": "Sinyal durumu değişmiş", "signal_id": signal_id_str}
            logger.info("signal_approved", signal_id=signal_id_str, user=user)

            # Executor'a bildir
            await publish(
                "signal:approved",
                {
                    "signal_id": signal_id_str,
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "entry_price": float(signal.entry_price),
                    "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
                    "take_profit": float(signal.take_profit) if signal.take_profit else None,
                    "confidence": float(signal.confidence),
                },
            )

            return {
                "success": True,
                "message": f"Sinyal onaylandı — {signal.symbol} {signal.side}",
                "signal_id": signal_id_str,
            }
        else:
            await repo.update_status(signal_id, SignalStatus.REJECTED, expected_status=SignalStatus.PENDING)
            logger.info("signal_rejected", signal_id=signal_id_str, user=user)

            return {
                "success": True,
                "message": f"Sinyal reddedildi - {signal.symbol} {signal.side}",
                "signal_id": signal_id_str,
            }


def parse_callback_data(callback_data: str) -> tuple[str, str] | None:
    """Callback verisini parse et.

    Format: "approve:{signal_id}" veya "reject:{signal_id}"

    Returns:
        (action, signal_id) tuple veya None
    """
    try:
        parts = callback_data.split(":", 1)
        if len(parts) != 2:
            return None
        action, signal_id = parts
        if action not in (CALLBACK_APPROVE, CALLBACK_REJECT):
            return None
        # UUID validasyonu
        uuid.UUID(signal_id)
        return action, signal_id
    except (ValueError, IndexError):
        return None
