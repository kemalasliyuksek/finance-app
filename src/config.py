"""Merkezi konfigürasyon - Pydantic Settings ile type-safe, env-based."""

from __future__ import annotations

import json
import warnings
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_JWT_INSECURE_DEFAULT = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Uygulama ---
    app_mode: Literal["live", "sandbox", "testnet", "backtest"] = "sandbox"
    trading_mode: Literal["semi_auto", "full_auto"] = "semi_auto"
    log_level: str = "INFO"

    # --- Binance API ---
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet_api_key: str = ""
    binance_testnet_api_secret: str = ""

    # --- Veritabanı ---
    database_url: str = "postgresql+asyncpg://trading_bot:changeme@localhost:5432/trading_bot"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/2"

    # --- Telegram ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- CryptoPanic ---
    cryptopanic_api_key: str = ""

    # --- Sentry/GlitchTip ---
    sentry_dsn: str = ""

    # --- Trading Parametreleri ---
    trading_pairs: list[str] = Field(default=["BTCUSDT", "ETHUSDT"])
    candle_intervals: list[str] = Field(default=["15m", "1h"])

    # --- Strateji Parametreleri ---
    ema_fast_period: int = 9
    ema_slow_period: int = 21
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    bb_period: int = 20
    bb_std_dev: float = 2.0
    volume_spike_multiplier: float = 1.5
    min_signal_confidence: float = 0.40

    # MACD parametreleri
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9

    # EMA trend skoru (crossover olmadan)
    ema_trend_score: float = 0.6

    # ATR bazlı SL/TP
    atr_sl_multiplier: float = 1.5     # SL = entry ± ATR × bu değer
    atr_tp_multiplier: float = 3.0     # TP = entry ± ATR × bu değer (2:1 R:R)
    min_sl_pct: float = 0.005          # Min %0.5 SL mesafesi
    max_sl_pct: float = 0.05           # Max %5 SL mesafesi
    min_tp_pct: float = 0.03           # Min %3 TP mesafesi

    # BB Squeeze
    bb_squeeze_percentile: float = 0.20   # Bu percentile altı = squeeze
    bb_squeeze_lookback: int = 20          # Kaç mum geriye bak

    # Volume Breakout
    volume_breakout_max_ratio: float = 5.0  # Normalizasyon max oranı
    volume_min_intensity: float = 0.3       # Bu altında amplify etme

    # Trailing Stop
    trailing_stop_activation_pct: float = 2.0   # %2 kârda aktive ol
    trailing_stop_trail_pct: float = 2.0        # Zirveden %2 düşüşte sat
    trailing_stop_lookback: int = 10            # Son kaç mumun zirvesine bak

    # Zaman Bazlı Çıkış
    max_hold_hours: int = 4                     # Max pozisyon tutma süresi
    time_exit_min_profit_pct: float = 0.5       # Bu kâr altındaysa çık (%)

    # Strateji bileşen ağırlıkları (toplam = 1.0)
    strategy_w_ema: float = 0.25
    strategy_w_macd: float = 0.25
    strategy_w_rsi: float = 0.20
    strategy_w_bb: float = 0.15
    strategy_w_volume: float = 0.15

    # --- Risk Parametreleri ---
    risk_per_trade_pct: float = 0.02
    max_concurrent_positions: int = 2
    daily_loss_limit_pct: float = 0.05
    min_balance_usdt: float = 50.0
    max_asset_allocation_pct: float = 0.40
    cooldown_seconds: int = 300  # 5 dakika (coin bazlı)
    max_trades_per_day: int = 15

    # --- Screener ---
    screener_enabled: bool = True
    screener_interval_seconds: int = 300  # 5 dakika
    screener_min_volume_usdt: float = 500_000  # Min 24s hacim
    screener_min_change_pct: float = 2.0  # Min |fiyat değişimi| %
    screener_max_candidates: int = 40  # Deep analiz için max aday
    screener_active_dynamic_pairs: int = 15  # Dinamik aktif coin sayısı
    screener_volume_top_n: int = 5  # Her zaman aktif hacim top N
    screener_volume_top_min_usdt: float = 1_000_000  # Volume top liste için min hacim
    screener_composite_volume_weight: float = 0.60  # Composite skor: hacim ağırlığı
    screener_composite_momentum_weight: float = 0.40  # Composite skor: momentum ağırlığı
    screener_blacklist: list[str] = Field(default=[])
    screener_breakout_weight: float = 0.30  # Breakout skorunun sıralama ağırlığı

    # --- Sinyal Onay ---
    signal_approval_timeout_seconds: int = 300  # 5 dakika

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Dashboard & Auth ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:3003"])

    @field_validator("trading_pairs", "candle_intervals", "cors_origins", "screener_blacklist", mode="before")
    @classmethod
    def parse_json_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> "Settings":
        """JWT secret key güvenlik kontrolü."""
        if self.jwt_secret_key == _JWT_INSECURE_DEFAULT:
            if self.app_mode == "live":
                raise ValueError(
                    "JWT_SECRET_KEY üretim (live) ortamında varsayılan değerde bırakılamaz! "
                    "En az 32 karakterlik güvenli bir anahtar belirleyin."
                )
            warnings.warn(
                "JWT_SECRET_KEY varsayılan değerde — üretim ortamına geçmeden önce değiştirin.",
                stacklevel=2,
            )
        elif self.app_mode == "live" and len(self.jwt_secret_key) < 32:
            raise ValueError(
                "JWT_SECRET_KEY live ortamda en az 32 karakter olmalı "
                f"(şu an: {len(self.jwt_secret_key)} karakter)."
            )
        return self

    @model_validator(mode="after")
    def _validate_strategy_weights(self) -> "Settings":
        """Strateji ağırlıklarının toplamı 1.0 olmalı."""
        total = (
            self.strategy_w_ema
            + self.strategy_w_macd
            + self.strategy_w_rsi
            + self.strategy_w_bb
            + self.strategy_w_volume
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Strateji ağırlıkları toplamı 1.0 olmalı (şu an: {total:.2f}). "
                "STRATEGY_W_EMA + STRATEGY_W_MACD + STRATEGY_W_RSI + STRATEGY_W_BB + STRATEGY_W_VOLUME = 1.0"
            )
        return self

    @model_validator(mode="after")
    def _validate_screener_composite_weights(self) -> "Settings":
        """Screener composite ağırlıklarının toplamı 1.0 olmalı."""
        total = self.screener_composite_volume_weight + self.screener_composite_momentum_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Screener composite ağırlıkları toplamı 1.0 olmalı (şu an: {total:.2f})."
            )
        return self

    @model_validator(mode="after")
    def _validate_sl_tp_bounds(self) -> "Settings":
        """SL min/max ve ATR çarpanları tutarlı olmalı."""
        if self.max_sl_pct <= self.min_sl_pct:
            raise ValueError(
                f"MAX_SL_PCT ({self.max_sl_pct}) > MIN_SL_PCT ({self.min_sl_pct}) olmalı."
            )
        if self.atr_tp_multiplier <= self.atr_sl_multiplier:
            raise ValueError(
                f"ATR_TP_MULTIPLIER ({self.atr_tp_multiplier}) > "
                f"ATR_SL_MULTIPLIER ({self.atr_sl_multiplier}) olmalı (R:R > 1)."
            )
        return self

    @property
    def is_testnet(self) -> bool:
        return self.app_mode == "testnet"

    @property
    def is_sandbox(self) -> bool:
        return self.app_mode == "sandbox"

    @property
    def active_api_key(self) -> str:
        if self.is_testnet:
            return self.binance_testnet_api_key
        if self.is_sandbox:
            return ""  # Sandbox keyless mainnet client kullanır
        return self.binance_api_key

    @property
    def active_api_secret(self) -> str:
        if self.is_testnet:
            return self.binance_testnet_api_secret
        if self.is_sandbox:
            return ""
        return self.binance_api_secret


settings = Settings()
