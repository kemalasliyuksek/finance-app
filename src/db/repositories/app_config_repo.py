"""AppConfig repository — DB-backed dinamik ayarların okuma/yazma katmanı."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.app_config import AppConfig

logger = get_logger("app_config_repo")


# 27 düzenlenebilir parametrenin merkezi listesi.
# Endpoint, migration, lifespan ve dashboard buradan okur.
APP_CONFIG_FIELDS: tuple[str, ...] = (
    # Risk (6)
    "risk_per_trade_pct",
    "max_concurrent_positions",
    "daily_loss_limit_pct",
    "min_balance_usdt",
    "cooldown_seconds",
    "max_trades_per_day",
    # Strateji (7)
    "min_signal_confidence",
    "strategy_w_ema",
    "strategy_w_macd",
    "strategy_w_rsi",
    "strategy_w_bb",
    "strategy_w_volume",
    "ema_trend_score",
    # SL/TP (5)
    "min_sl_pct",
    "max_sl_pct",
    "min_tp_pct",
    "atr_sl_multiplier",
    "atr_tp_multiplier",
    # Exit (4)
    "trailing_stop_activation_pct",
    "trailing_stop_trail_pct",
    "max_hold_hours",
    "time_exit_min_profit_pct",
    # Screener (4)
    "screener_min_volume_usdt",
    "screener_min_change_pct",
    "screener_active_dynamic_pairs",
    "screener_max_candidates",
    # Mode (1)
    "trading_mode",
)


class AppConfigRepository:
    """Tek satır config tablosu için CRUD."""

    FIELDS: tuple[str, ...] = APP_CONFIG_FIELDS

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_row(self) -> AppConfig | None:
        stmt = sa.select(AppConfig).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_seed_defaults(self, defaults: dict[str, Any]) -> AppConfig:
        """İlk kayıt yoksa defaults ile oluştur, varsa döndür.

        İdempotent: redeploy'larda mevcut değerleri bozmaz. Migration 008
        zaten tek satır yerleştirdiği için bu fonksiyon normalde sadece
        mevcut satırı okur; ancak migration öncesi manuel silme durumunda
        güvenlik ağı olarak seed mantığı korunur.
        """
        row = await self._get_row()
        if row is not None:
            return row

        # Sadece FIELDS içindeki anahtarları kullan (güvenlik)
        payload = {k: defaults[k] for k in self.FIELDS if k in defaults}
        row = AppConfig(**payload)
        self.session.add(row)
        await self.session.flush()
        logger.info("app_config_seeded", fields=len(payload))
        return row

    async def get_current(self) -> AppConfig:
        """Mevcut config satırını döndür — yoksa RuntimeError fırlatır."""
        row = await self._get_row()
        if row is None:
            raise RuntimeError(
                "app_config tablosu boş — migration 008 çalıştırıldı mı?"
            )
        return row

    async def update(self, updates: dict[str, Any], user: str) -> AppConfig:
        """Kısmi güncelleme — sadece FIELDS içindeki anahtarları kabul eder."""
        row = await self.get_current()
        applied = 0
        for key, value in updates.items():
            if key in self.FIELDS:
                setattr(row, key, value)
                applied += 1
        row.updated_by = user
        await self.session.flush()
        logger.info("app_config_updated", applied=applied, user=user)
        return row

    def to_settings_dict(self, row: AppConfig) -> dict[str, Any]:
        """DB satırını settings'e uygulanabilir dict'e çevir."""
        return {k: getattr(row, k) for k in self.FIELDS}
