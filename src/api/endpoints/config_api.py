"""Konfigürasyon ve bot durumu endpoint'leri."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError

from src.api.dependencies import get_current_active_user
from src.api.middleware.rate_limit import limiter
from src.config import settings
from src.core.audit import log_audit
from src.core.config_reload import (
    CONFIG_UPDATED_CHANNEL,
    apply_config_to_settings,
    validate_config_updates,
)
from src.core.events import publish
from src.core.logging import get_logger
from src.db.repositories.app_config_repo import (
    APP_CONFIG_FIELDS,
    AppConfigRepository,
)
from src.db.session import get_session

logger = get_logger("config_api")

router = APIRouter(tags=["config"])

_app_start_time = datetime.now(timezone.utc)


class TradingConfig(BaseModel):
    """GET /config yanıtı — sabit alanlar (env) + 27 düzenlenebilir alan."""

    # Env-only alanlar (read-only bilgi amaçlı)
    app_mode: str
    trading_pairs: list[str]
    candle_intervals: list[str]

    # --- Düzenlenebilir: Risk (6) ---
    risk_per_trade_pct: float
    max_concurrent_positions: int
    daily_loss_limit_pct: float
    min_balance_usdt: float
    cooldown_seconds: int
    max_trades_per_day: int

    # --- Düzenlenebilir: Strateji (7) ---
    min_signal_confidence: float
    strategy_w_ema: float
    strategy_w_macd: float
    strategy_w_rsi: float
    strategy_w_bb: float
    strategy_w_volume: float
    ema_trend_score: float

    # --- Düzenlenebilir: SL/TP (5) ---
    min_sl_pct: float
    max_sl_pct: float
    min_tp_pct: float
    atr_sl_multiplier: float
    atr_tp_multiplier: float

    # --- Düzenlenebilir: Exit (4) ---
    trailing_stop_activation_pct: float
    trailing_stop_trail_pct: float
    max_hold_hours: int
    time_exit_min_profit_pct: float

    # --- Düzenlenebilir: Screener (4) ---
    screener_min_volume_usdt: float
    screener_min_change_pct: float
    screener_active_dynamic_pairs: int
    screener_max_candidates: int

    # --- Düzenlenebilir: Mode (1) ---
    trading_mode: str


class TradingConfigUpdate(BaseModel):
    """PATCH /config body'si — kısmi güncelleme, tüm alanlar opsiyonel.

    Field constraint'leri defense-in-depth için buradadır; ek olarak
    Settings model_validator'ları (strategy_w_* toplamı, SL bounds vs.)
    `apply_config_to_settings` içinde çalıştırılır.
    """

    model_config = {"extra": "forbid"}  # Bilinmeyen alanlar reddedilir

    # Risk (6)
    risk_per_trade_pct: float | None = Field(None, ge=0.001, le=0.10)
    max_concurrent_positions: int | None = Field(None, ge=1, le=10)
    daily_loss_limit_pct: float | None = Field(None, ge=0.01, le=0.50)
    min_balance_usdt: float | None = Field(None, ge=5, le=10000)
    cooldown_seconds: int | None = Field(None, ge=0, le=86400)
    max_trades_per_day: int | None = Field(None, ge=1, le=100)

    # Strateji (7)
    min_signal_confidence: float | None = Field(None, ge=0.1, le=1.0)
    strategy_w_ema: float | None = Field(None, ge=0.0, le=1.0)
    strategy_w_macd: float | None = Field(None, ge=0.0, le=1.0)
    strategy_w_rsi: float | None = Field(None, ge=0.0, le=1.0)
    strategy_w_bb: float | None = Field(None, ge=0.0, le=1.0)
    strategy_w_volume: float | None = Field(None, ge=0.0, le=1.0)
    ema_trend_score: float | None = Field(None, ge=0.0, le=1.0)

    # SL/TP (5)
    min_sl_pct: float | None = Field(None, ge=0.001, le=0.10)
    max_sl_pct: float | None = Field(None, ge=0.005, le=0.20)
    min_tp_pct: float | None = Field(None, ge=0.001, le=0.20)
    atr_sl_multiplier: float | None = Field(None, ge=0.5, le=10)
    atr_tp_multiplier: float | None = Field(None, ge=0.5, le=20)

    # Exit (4)
    trailing_stop_activation_pct: float | None = Field(None, ge=0.1, le=20)
    trailing_stop_trail_pct: float | None = Field(None, ge=0.1, le=20)
    max_hold_hours: int | None = Field(None, ge=1, le=168)
    time_exit_min_profit_pct: float | None = Field(None, ge=0.0, le=10)

    # Screener (4)
    screener_min_volume_usdt: float | None = Field(None, ge=10_000, le=100_000_000)
    screener_min_change_pct: float | None = Field(None, ge=0.0, le=50)
    screener_active_dynamic_pairs: int | None = Field(None, ge=1, le=50)
    screener_max_candidates: int | None = Field(None, ge=5, le=200)

    # Mode (1)
    trading_mode: Literal["semi_auto", "full_auto"] | None = None


class BotStatus(BaseModel):
    app_mode: str
    trading_mode: str
    uptime_seconds: int
    active_pairs: list[str]
    candle_intervals: list[str]
    is_sandbox: bool = False


class AddPairRequest(BaseModel):
    symbol: str


def _build_config_response() -> TradingConfig:
    """Mevcut settings'ten TradingConfig response'u oluştur."""
    return TradingConfig(
        app_mode=settings.app_mode,
        trading_pairs=settings.trading_pairs,
        candle_intervals=settings.candle_intervals,
        **{k: getattr(settings, k) for k in APP_CONFIG_FIELDS},
    )


@router.get("", response_model=TradingConfig)
async def get_config(
    _user: str = Depends(get_current_active_user),
) -> TradingConfig:
    """Mevcut trading konfigürasyonu — settings singleton'dan okunur."""
    return _build_config_response()


@router.patch("", response_model=TradingConfig)
@limiter.limit("10/minute")
async def update_config(
    request: Request,
    body: TradingConfigUpdate,
    user: str = Depends(get_current_active_user),
) -> TradingConfig:
    """Trading konfigürasyonunu kısmi güncelle.

    Akış:
    1. Pydantic field constraint'leri otomatik çalışır (422 fırlatır)
    2. DB'ye yaz (AppConfigRepository)
    3. Audit log
    4. Yerel settings'i güncelle (Settings model_validator'ları çalışır; geçersizse 422)
    5. Redis `config:updated` publish → diğer container'lar + dashboard WS
    """
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Güncellenecek alan yok",
        )

    # 1) Cross-field validator'ları settings'e dokunmadan çalıştır
    try:
        validate_config_updates(updates)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors(),
        )

    # 2) DB'ye yaz + audit
    try:
        async with get_session() as session:
            repo = AppConfigRepository(session)
            current = await repo.get_current()
            old_values = {k: getattr(current, k) for k in updates}
            await repo.update(updates, user=user)
            await log_audit(
                session,
                action="update",
                entity_type="config",
                entity_id="app_config",
                user=user,
                changes={
                    k: {"old": old_values[k], "new": v} for k, v in updates.items()
                },
            )
    except Exception:
        logger.exception("app_config_db_update_failed", updates=list(updates.keys()))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Konfigürasyon veritabanına yazılamadı",
        )

    # 3) Yerel settings'i güncelle (DB başarılıysa)
    await apply_config_to_settings(updates)

    # 4) Diğer container'lara + dashboard WS'ye bildir
    await publish(
        CONFIG_UPDATED_CHANNEL,
        {"changes": updates, "updated_by": user},
    )

    return _build_config_response()


@router.get("/status", response_model=BotStatus)
async def bot_status(
    _user: str = Depends(get_current_active_user),
) -> BotStatus:
    """Bot durumu."""
    uptime = int((datetime.now(timezone.utc) - _app_start_time).total_seconds())
    return BotStatus(
        app_mode=settings.app_mode,
        trading_mode=settings.trading_mode,
        uptime_seconds=uptime,
        active_pairs=settings.trading_pairs,
        candle_intervals=settings.candle_intervals,
        is_sandbox=settings.is_sandbox,
    )


@router.get("/pairs", response_model=list[str])
async def list_pairs(
    _user: str = Depends(get_current_active_user),
) -> list[str]:
    """Aktif trading çiftleri."""
    return settings.trading_pairs


@router.post("/pairs", response_model=list[str], status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def add_pair(
    request: Request,
    body: AddPairRequest,
    _user: str = Depends(get_current_active_user),
) -> list[str]:
    """Trading çifti ekle."""
    symbol = body.symbol.upper()
    if symbol in settings.trading_pairs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{symbol} zaten mevcut",
        )
    settings.trading_pairs.append(symbol)
    await publish(
        "config:pairs_updated",
        {"pairs": settings.trading_pairs, "action": "add", "symbol": symbol},
    )
    return settings.trading_pairs


@router.delete("/pairs/{symbol}", response_model=list[str])
@limiter.limit("5/minute")
async def remove_pair(
    request: Request,
    symbol: str,
    _user: str = Depends(get_current_active_user),
) -> list[str]:
    """Trading çifti sil."""
    symbol = symbol.upper()
    if symbol not in settings.trading_pairs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{symbol} bulunamadı",
        )
    settings.trading_pairs.remove(symbol)
    await publish(
        "config:pairs_updated",
        {"pairs": settings.trading_pairs, "action": "remove", "symbol": symbol},
    )
    return settings.trading_pairs
