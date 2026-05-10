"""AppConfig modeli — DB-backed dinamik ayar deposu (tek satır)."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class AppConfig(Base, TimestampMixin):
    """Runtime'da düzenlenebilir trading parametreleri.

    Bu tablo tek satır içerir (uygulama seviyesinde garanti). İlk boot'ta
    `get_or_seed_defaults` ile mevcut `settings` değerleriyle doldurulur.
    Redeploy'larda mevcut kayıt korunur — reset olmaz.
    """

    __tablename__ = "app_config"
    __table_args__ = {"schema": "trading"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # --- Risk Parametreleri (6) ---
    risk_per_trade_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_concurrent_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_loss_limit_pct: Mapped[float] = mapped_column(Float, nullable=False)
    min_balance_usdt: Mapped[float] = mapped_column(Float, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Strateji Parametreleri (7) ---
    min_signal_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    strategy_w_ema: Mapped[float] = mapped_column(Float, nullable=False)
    strategy_w_macd: Mapped[float] = mapped_column(Float, nullable=False)
    strategy_w_rsi: Mapped[float] = mapped_column(Float, nullable=False)
    strategy_w_bb: Mapped[float] = mapped_column(Float, nullable=False)
    strategy_w_volume: Mapped[float] = mapped_column(Float, nullable=False)
    ema_trend_score: Mapped[float] = mapped_column(Float, nullable=False)

    # --- SL/TP Parametreleri (5) ---
    min_sl_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_sl_pct: Mapped[float] = mapped_column(Float, nullable=False)
    min_tp_pct: Mapped[float] = mapped_column(Float, nullable=False)
    atr_sl_multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    atr_tp_multiplier: Mapped[float] = mapped_column(Float, nullable=False)

    # --- Exit Parametreleri (4) ---
    trailing_stop_activation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    trailing_stop_trail_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_hold_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    time_exit_min_profit_pct: Mapped[float] = mapped_column(Float, nullable=False)

    # --- Screener Parametreleri (4) ---
    screener_min_volume_usdt: Mapped[float] = mapped_column(Float, nullable=False)
    screener_min_change_pct: Mapped[float] = mapped_column(Float, nullable=False)
    screener_active_dynamic_pairs: Mapped[int] = mapped_column(Integer, nullable=False)
    screener_max_candidates: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Trading Mode (1) ---
    trading_mode: Mapped[str] = mapped_column(String(20), nullable=False)

    # Audit
    updated_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
