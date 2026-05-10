"""Ana uygulama giriş noktası - FastAPI + background worker'lar."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.router import api_router
from src.api.ws_manager import ws_manager
from src.config import settings
from src.core.events import close_redis
from src.core.logging import get_logger, setup_logging

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Uygulama yaşam döngüsü - başlangıç ve kapanış."""
    setup_logging()
    logger.info(
        "trading_bot_starting",
        app_mode=settings.app_mode,
        trading_mode=settings.trading_mode,
        pairs=settings.trading_pairs,
        intervals=settings.candle_intervals,
    )

    # Default admin kullanıcı oluştur (yoksa)
    import secrets
    from src.db.repositories.user_repo import UserRepository
    from src.api.auth import hash_password
    from src.db.session import get_session

    try:
        async with get_session() as session:
            user_repo = UserRepository(session)
            user_count = await user_repo.count()
            if user_count == 0:
                generated_password = secrets.token_urlsafe(16)
                default_hash = hash_password(generated_password)
                await user_repo.create(
                    username="admin",
                    password_hash=default_hash,
                    role="admin",
                    must_change_password=True,
                )
                logger.warning(
                    "default_admin_created",
                    username="admin",
                    password=generated_password,
                    msg="Bu şifreyi not alın ve ilk girişte değiştirin!",
                )
    except Exception:
        logger.exception("default_admin_creation_error")

    # App config: DB'den yükle (yoksa default'larla seed et)
    try:
        from src.db.repositories.app_config_repo import (
            APP_CONFIG_FIELDS,
            AppConfigRepository,
        )
        from src.core.config_reload import apply_config_to_settings

        async with get_session() as session:
            cfg_repo = AppConfigRepository(session)
            # Güvenlik ağı: migration 008 zaten satır oluşturdu ama silinmiş olabilir
            defaults = {k: getattr(settings, k) for k in APP_CONFIG_FIELDS}
            row = await cfg_repo.get_or_seed_defaults(defaults)
            db_values = cfg_repo.to_settings_dict(row)

        # Settings singleton'ını DB değerleriyle güncelle
        await apply_config_to_settings(db_values)
        logger.info(
            "app_config_loaded_from_db",
            trading_mode=settings.trading_mode,
            min_signal_confidence=settings.min_signal_confidence,
            risk_per_trade_pct=settings.risk_per_trade_pct,
        )
    except Exception:
        logger.exception(
            "app_config_init_failed",
            msg="settings singleton in-memory default'larda kalacak",
        )

    # Sentry/GlitchTip başlat
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.1,
            environment=settings.app_mode,
        )
        logger.info("sentry_initialized")

    # Background worker'ları başlat
    import asyncio
    from src.collector.rest_fetcher import create_binance_client, fetch_historical_klines
    from src.collector.rest_poller import RestPoller
    from src.strategy.signal_generator import SignalGenerator
    from src.sentiment.sentiment_engine import SentimentEngine
    from src.executor.binance_client import close_binance_client
    from src.db.repositories.candle_repo import CandleRepository
    from src.db.session import get_session

    tasks: list[asyncio.Task] = []
    poller = None
    signal_gen = None
    sentiment_eng = None
    screener_worker = None

    if settings.app_mode != "backtest":
        try:
            # Binance client
            client = await create_binance_client()

            # 1) Tarihsel veri backfill (arka planda paralel — API'yi bloklamaz)
            async def _run_backfill() -> None:
                """Tüm pair/interval çiftleri için paralel backfill."""
                backfill_tasks = []
                for symbol in settings.trading_pairs:
                    for interval in settings.candle_intervals:
                        backfill_tasks.append(
                            _backfill_single(client, symbol, interval)
                        )
                await asyncio.gather(*backfill_tasks, return_exceptions=True)
                logger.info("backfill_all_complete", pair_count=len(backfill_tasks))

            async def _backfill_single(c: object, symbol: str, interval: str) -> None:
                try:
                    candles = await fetch_historical_klines(c, symbol, interval)
                    async with get_session() as session:
                        repo = CandleRepository(session)
                        count = await repo.upsert_many(candles)
                        logger.info("backfill_complete", symbol=symbol, interval=interval, count=count)
                except Exception:
                    logger.exception("backfill_error", symbol=symbol, interval=interval)

            tasks.append(asyncio.create_task(_run_backfill(), name="backfill"))

            # 2) REST poller - periyodik mum verisi çekme (WebSocket yerine)
            poller = RestPoller(client)
            await poller.start()

            # 3) Sinyal üretici
            signal_gen = SignalGenerator()
            tasks.append(asyncio.create_task(signal_gen.start(), name="signal_generator"))

            # 3b) Periyodik sinyal expire kontrolü
            async def _expire_loop() -> None:
                """Süresi dolmuş pending sinyalleri otomatik expire et."""
                import asyncio as _aio
                from src.db.repositories.signal_repo import SignalRepository as _SigRepo
                while True:
                    try:
                        async with get_session() as session:
                            repo = _SigRepo(session)
                            count = await repo.expire_old_signals()
                            if count:
                                logger.info("signals_auto_expired", count=count)
                    except Exception:
                        logger.exception("signal_expire_loop_error")
                    await _aio.sleep(30)  # Her 30 saniyede kontrol

            tasks.append(asyncio.create_task(_expire_loop(), name="signal_expire_loop"))

            # 3c) Emir yürütme worker'ı (onaylanan sinyalleri çalıştırır)
            from src.workers.execution_worker import ExecutionWorker
            execution_worker = ExecutionWorker()
            tasks.append(asyncio.create_task(execution_worker.start(), name="execution_worker"))

            # 3d) Config reload listener — dashboard PATCH sonrası settings'i hot reload
            from src.core.config_reload import config_listener
            tasks.append(asyncio.create_task(config_listener(), name="config_listener"))

            # 4) Sentiment motoru
            sentiment_eng = SentimentEngine()
            tasks.append(asyncio.create_task(sentiment_eng.start(), name="sentiment_engine"))

            # 5) WebSocket Redis bridge
            await ws_manager.start()

            # 6) Sandbox modu bilgilendirme
            if settings.is_sandbox:
                logger.info(
                    "sandbox_mode_active",
                    msg="Sandbox modu aktif — emirler lokal simüle edilir, Binance'e gönderilmez",
                )

            # 6b) Periyodik portfolio snapshot (her 5 dakikada)
            async def _snapshot_loop() -> None:
                """Periyodik bakiye snapshot'ı oluştur."""
                import asyncio as _aio
                from src.portfolio.balance_tracker import BalanceTracker
                tracker = BalanceTracker()
                await _aio.sleep(60)  # İlk snapshot için 60s bekle (market cache dolsun)
                while True:
                    try:
                        await tracker.take_snapshot()
                    except Exception:
                        logger.exception("snapshot_loop_error")
                    await _aio.sleep(300)  # 5 dakikada bir

            tasks.append(asyncio.create_task(_snapshot_loop(), name="snapshot_loop"))

            # 7) Screener worker (dinamik coin keşfi)
            if settings.screener_enabled:
                from src.screener.screener_worker import ScreenerWorker

                screener_worker = ScreenerWorker(client, poller, signal_gen)
                tasks.append(
                    asyncio.create_task(screener_worker.start(), name="screener")
                )
                logger.info("screener_worker_enabled")

            logger.info("all_workers_started", worker_count=len(tasks) + 2)

            # 8) Startup recovery — onaylanmış ama işlenmemiş sinyalleri yeniden yayınla
            try:
                from src.db.repositories.signal_repo import SignalRepository
                from src.constants import SignalStatus
                from src.core.events import publish
                from datetime import datetime, timezone

                async with get_session() as session:
                    sig_repo = SignalRepository(session)
                    orphaned = await sig_repo.get_approved_without_orders()
                    recovered = 0
                    expired = 0
                    now_naive = datetime.utcnow()
                    for sig in orphaned:
                        # Timezone-safe karşılaştırma: her ikisini de naive UTC'ye çevir
                        exp = sig.expires_at.replace(tzinfo=None) if sig.expires_at and sig.expires_at.tzinfo else sig.expires_at
                        if exp and exp < now_naive:
                            await sig_repo.update_status(sig.id, SignalStatus.EXPIRED)
                            expired += 1
                            continue
                        await publish(
                            "signal:approved",
                            {
                                "signal_id": str(sig.id),
                                "symbol": sig.symbol,
                                "side": sig.side,
                                "entry_price": float(sig.entry_price),
                                "stop_loss": float(sig.stop_loss) if sig.stop_loss else None,
                                "take_profit": float(sig.take_profit) if sig.take_profit else None,
                                "confidence": float(sig.confidence),
                            },
                        )
                        recovered += 1
                        logger.info("recovery_replaying_signal", signal_id=str(sig.id), symbol=sig.symbol)
                    if recovered or expired:
                        logger.info("startup_recovery_complete", recovered=recovered, expired=expired)
            except Exception:
                logger.exception("startup_recovery_error")

        except Exception:
            logger.exception("worker_startup_error")

    yield

    # Kapanış - tüm worker'ları durdur
    logger.info("trading_bot_shutting_down")
    await ws_manager.stop()
    if poller:
        await poller.stop()
    if signal_gen:
        await signal_gen.stop()
    if sentiment_eng:
        await sentiment_eng.stop()
    if screener_worker:
        await screener_worker.stop()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await close_binance_client()
    await close_redis()


def create_app() -> FastAPI:
    """FastAPI uygulaması oluştur."""
    app = FastAPI(
        title="Finance App - Trading Bot",
        description="Binance kripto trading bot API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Rate limiting
    from src.api.middleware.rate_limit import limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=3600,
    )

    # API rotaları
    app.include_router(api_router)

    # Prometheus metrikleri /metrics endpoint'inde
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_mode != "live",
        log_level=settings.log_level.lower(),
    )
