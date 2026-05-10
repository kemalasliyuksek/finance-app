"""Sinyal üretici - Redis event'lerini dinler, strateji çalıştırır."""

from __future__ import annotations

import json

import redis.asyncio as aioredis

from src.analysis.ta_engine import TAResult, candles_to_dataframe, run_analysis
from src.config import settings
from src.constants import RedisChannel, Side
from src.core.events import get_cache, get_redis, publish
from src.core.logging import get_logger
from src.core.metrics import signal_confidence, signals_total
from src.db.repositories.candle_repo import CandleRepository
from src.db.repositories.signal_repo import SignalRepository
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_session
from src.schemas.signal import SignalCreate
from src.strategy.ema_crossover import EMACrossoverStrategy

logger = get_logger("signal_generator")


class SignalGenerator:
    """Mum kapanışlarını dinler, analiz yapar, sinyal üretir."""

    def __init__(self) -> None:
        self.strategy = EMACrossoverStrategy()
        self._running = False
        self._pubsub = None
        self._recent_exit_trades: dict[str, float] = {}  # trade_id → timestamp

    async def start(self) -> None:
        """Redis pub/sub üzerinden mum kapanış event'lerini dinlemeye başla."""
        self._running = True
        r = await get_redis()
        self._pubsub = r.pubsub()

        # Tüm trading çiftleri ve interval'ler için subscribe
        channels = []
        for symbol in settings.trading_pairs:
            for interval in settings.candle_intervals:
                channel = RedisChannel.candle_closed(symbol, interval)
                channels.append(channel)

        if channels:
            await self._pubsub.subscribe(*channels)
        logger.info("signal_generator_subscribed", channels=channels)

        try:
            async for message in self._pubsub.listen():
                if not self._running:
                    break
                if message["type"] != "message":
                    continue
                await self._handle_candle_closed(message)
        finally:
            if self._pubsub:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()

    async def stop(self) -> None:
        self._running = False

    async def subscribe_pair(self, symbol: str) -> None:
        """Yeni çiftin candle:closed kanallarına subscribe ol."""
        if not self._pubsub:
            return
        channels = [
            RedisChannel.candle_closed(symbol, interval)
            for interval in settings.candle_intervals
        ]
        await self._pubsub.subscribe(*channels)
        logger.info("signal_gen_pair_subscribed", symbol=symbol, channels=channels)

    async def unsubscribe_pair(self, symbol: str) -> None:
        """Çiftin candle:closed kanallarından unsubscribe ol."""
        if not self._pubsub:
            return
        channels = [
            RedisChannel.candle_closed(symbol, interval)
            for interval in settings.candle_intervals
        ]
        await self._pubsub.unsubscribe(*channels)
        logger.info("signal_gen_pair_unsubscribed", symbol=symbol, channels=channels)

    async def _handle_candle_closed(self, message: dict) -> None:
        """Mum kapanış event'ini işle - analiz yap, sinyal üret."""
        try:
            data = json.loads(message["data"])
            symbol = data["symbol"]
            interval = data["interval"]
        except (json.JSONDecodeError, KeyError):
            logger.error("invalid_candle_event", message=message)
            return

        logger.debug("processing_candle_close", symbol=symbol, interval=interval)

        try:
            # Açık pozisyon kontrolü
            async with get_session() as session:
                trade_repo = TradeRepository(session)
                open_trades = await trade_repo.get_open_trades(symbol=symbol)

            has_open_position = len(open_trades) > 0

            logger.info(
                "position_check",
                symbol=symbol,
                interval=interval,
                has_open=has_open_position,
                open_count=len(open_trades),
            )

            if has_open_position:
                # Açık pozisyon var → çıkış sinyali kontrol et (SELL)
                await self._check_exit_signals(symbol, interval, open_trades)
            else:
                # Açık pozisyon yok → giriş sinyali üret (sadece BUY)
                signal = await self._generate_signal(symbol, interval)
                if signal and signal.side == Side.SELL:
                    # Pozisyon yokken SELL sinyali anlamsız — atla
                    logger.debug(
                        "sell_signal_skipped_no_position",
                        symbol=symbol,
                        interval=interval,
                        confidence=float(signal.confidence),
                    )
                    signal = None
                if signal:
                    is_actionable = float(signal.confidence) >= settings.min_signal_confidence
                    await self._save_signal(signal, actionable=is_actionable)
                    if is_actionable:
                        await self._publish_signal(signal)
        except Exception:
            logger.exception(
                "signal_generation_error", symbol=symbol, interval=interval
            )

    async def _generate_signal(
        self, symbol: str, interval: str
    ) -> SignalCreate | None:
        """Belirli bir çift ve interval için sinyal üret."""
        # 1) DB'den son mumları getir
        async with get_session() as session:
            repo = CandleRepository(session)
            candles = await repo.get_recent(symbol, interval, limit=200)

        if len(candles) < 30:
            logger.warning(
                "not_enough_candles",
                symbol=symbol,
                interval=interval,
                count=len(candles),
            )
            return None

        # 2) DataFrame'e dönüştür ve analiz yap
        df = candles_to_dataframe(candles)
        ta_result = run_analysis(df, symbol=symbol, interval=interval)

        # 3) Sentiment skoru al (Redis cache'den, API key varsa)
        sentiment = None
        if settings.cryptopanic_api_key:
            sentiment = await self._get_sentiment(symbol)

        # 4) Strateji çalıştır
        signal = self.strategy.evaluate(ta_result, sentiment_score=sentiment)

        if signal:
            is_actionable = float(signal.confidence) >= settings.min_signal_confidence
            logger.info(
                "signal_generated",
                symbol=symbol,
                interval=interval,
                side=signal.side,
                confidence=float(signal.confidence),
                actionable=is_actionable,
                entry=float(signal.entry_price),
                sl=float(signal.stop_loss) if signal.stop_loss else None,
                tp=float(signal.take_profit) if signal.take_profit else None,
            )

        return signal

    async def _get_sentiment(self, symbol: str) -> float | None:
        """Redis cache'den sentiment skoru al."""
        key = RedisChannel.sentiment(symbol)
        data = await get_cache(key)
        if data and isinstance(data, dict):
            return data.get("score")
        return None

    async def _save_signal(self, signal: SignalCreate, *, actionable: bool) -> None:
        """Sinyali DB'ye kaydet. Düşük güvenli sinyaller 'weak' status ile kaydedilir."""
        from src.constants import SignalStatus

        async with get_session() as session:
            repo = SignalRepository(session)
            db_signal = await repo.create(signal)

            if not actionable:
                await repo.update_status(db_signal.id, SignalStatus.WEAK)
            elif settings.trading_mode == "full_auto":
                # Tam otomatik mod — sinyal direkt onaylanır
                await repo.update_status(
                    db_signal.id, SignalStatus.APPROVED,
                    approved_by="auto",
                    expected_status=SignalStatus.PENDING,
                )

            # Prometheus metrikleri
            signals_total.labels(
                symbol=signal.symbol,
                side=signal.side,
                strategy=signal.strategy,
                status="approved" if (actionable and settings.trading_mode == "full_auto") else "pending" if actionable else "weak",
            ).inc()
            signal_confidence.labels(strategy=signal.strategy).observe(
                float(signal.confidence)
            )

            self._last_signal_id = str(db_signal.id)

            logger.info(
                "signal_saved",
                signal_id=str(db_signal.id),
                symbol=signal.symbol,
                side=signal.side,
                actionable=actionable,
                auto_approved=actionable and settings.trading_mode == "full_auto",
            )

    async def _check_exit_signals(
        self, symbol: str, interval: str, open_trades: list | None = None,
    ) -> None:
        """Açık pozisyonlar için çıkış sinyali kontrol et."""
        if open_trades is None:
            async with get_session() as session:
                trade_repo = TradeRepository(session)
                open_trades = await trade_repo.get_open_trades(symbol=symbol)

        if not open_trades:
            return

        # Son mumları çek ve analiz yap
        async with get_session() as session:
            repo = CandleRepository(session)
            candles = await repo.get_recent(symbol, interval, limit=200)

        if len(candles) < 30:
            return

        df = candles_to_dataframe(candles)
        ta_result = run_analysis(df, symbol=symbol, interval=interval)

        import time
        from decimal import Decimal
        from datetime import datetime, timedelta, timezone

        # Eski kayıtları temizle (60 saniyeden eski)
        now_ts = time.monotonic()
        self._recent_exit_trades = {
            tid: ts for tid, ts in self._recent_exit_trades.items()
            if now_ts - ts < 60
        }

        for trade in open_trades:
            trade_id = str(trade.id)

            # Aynı trade için son 60 saniyede zaten exit sinyali üretildiyse atla
            if trade_id in self._recent_exit_trades:
                logger.debug(
                    "exit_signal_deduplicated",
                    symbol=symbol,
                    trade_id=trade_id,
                    interval=interval,
                )
                continue

            exit_signal = self.strategy.evaluate_exit(ta_result, trade)
            if exit_signal:
                # Bu trade için deduplikasyon kaydı oluştur
                self._recent_exit_trades[trade_id] = now_ts

                logger.info(
                    "exit_signal_generated",
                    symbol=symbol,
                    trade_id=trade_id,
                    reason=exit_signal.reason,
                    confidence=exit_signal.confidence,
                )

                exit_side = Side.SELL if trade.side == Side.BUY else Side.BUY
                signal = SignalCreate(
                    symbol=symbol,
                    side=exit_side,
                    strategy=f"exit_{exit_signal.reason}",
                    confidence=Decimal(str(round(exit_signal.confidence, 4))),
                    entry_price=Decimal(str(ta_result.current_price)),
                    stop_loss=None,
                    take_profit=None,
                    indicators=ta_result.to_dict(),
                    sentiment_score=None,
                    expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
                        + timedelta(seconds=settings.signal_approval_timeout_seconds),
                )
                await self._save_signal(signal, actionable=True)
                await self._publish_signal(signal)

    async def _publish_signal(self, signal: SignalCreate) -> None:
        """Eşik üstü sinyali Redis'e yayınla (Telegram + Dashboard)."""
        signal_data = {
            "signal_id": getattr(self, "_last_signal_id", ""),
            "symbol": signal.symbol,
            "side": signal.side,
            "confidence": float(signal.confidence),
            "entry_price": float(signal.entry_price),
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "take_profit": float(signal.take_profit) if signal.take_profit else None,
            "strategy": signal.strategy,
        }

        # Telegram + Dashboard bildirimi
        await publish(RedisChannel.SIGNAL_NEW, signal_data)

        # Tam otomatik mod — hemen execution worker'a gönder
        if settings.trading_mode == "full_auto":
            await publish("signal:approved", signal_data)
            logger.info(
                "signal_auto_approved",
                signal_id=signal_data["signal_id"],
                symbol=signal.symbol,
                side=signal.side,
            )
