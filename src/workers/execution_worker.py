"""Emir yürütme worker'ı — onaylanan sinyalleri emir olarak çalıştırır.

Redis "signal:approved" kanalını dinler ve RiskManager + OrderManager pipeline'ını tetikler.
Hem semi_auto (Telegram/Dashboard onay) hem full_auto (otomatik) modları destekler.
"""

from __future__ import annotations

import json
from decimal import Decimal

import redis.asyncio as aioredis

from src.config import settings
from src.constants import SignalStatus
from src.core.audit import log_audit
from src.core.events import get_redis
from src.core.logging import get_logger
from src.db.repositories.signal_repo import SignalRepository
from src.db.session import get_session
from src.executor.binance_client import get_usdt_balance
from src.executor.order_manager import OrderManager
from src.risk.risk_manager import RiskManager

logger = get_logger("execution_worker")


class ExecutionWorker:
    """Onaylanan sinyalleri dinler ve emir olarak çalıştırır."""

    def __init__(self) -> None:
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager()
        self._running = False

    async def start(self) -> None:
        """Redis signal:approved kanalını dinlemeye başla."""
        self._running = True
        r = await get_redis()
        pubsub = r.pubsub()

        await pubsub.subscribe("signal:approved", "signal:exit")
        logger.info("execution_worker_started", channels=["signal:approved", "signal:exit"])

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] != "message":
                    continue
                channel = message.get("channel", b"").decode() if isinstance(message.get("channel"), bytes) else message.get("channel", "")
                if channel == "signal:exit":
                    await self._handle_exit_signal(message)
                else:
                    await self._handle_approved_signal(message)
        finally:
            await pubsub.unsubscribe("signal:approved", "signal:exit")
            await pubsub.close()

    async def stop(self) -> None:
        self._running = False
        logger.info("execution_worker_stopped")

    async def _handle_approved_signal(self, message: dict) -> None:
        """Onaylanan sinyali işle — risk kontrolü + emir yürütme."""
        try:
            data = json.loads(message["data"])
            signal_id = data["signal_id"]
            symbol = data["symbol"]
            side = data["side"]
            entry_price = Decimal(str(data["entry_price"]))
            stop_loss = Decimal(str(data["stop_loss"])) if data.get("stop_loss") else None
            take_profit = Decimal(str(data["take_profit"])) if data.get("take_profit") else None
            confidence = float(data.get("confidence", 0))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("invalid_approved_signal", error=str(e), data=message.get("data"))
            return

        logger.info(
            "processing_approved_signal",
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            entry_price=float(entry_price),
        )

        # İdempotency: sinyal zaten işlendiyse atla
        try:
            import uuid as _uuid
            async with get_session() as session:
                repo = SignalRepository(session)
                signal_db = await repo.get_by_id(_uuid.UUID(signal_id))
                if not signal_db or signal_db.status in (SignalStatus.EXECUTED, SignalStatus.REJECTED, SignalStatus.EXPIRED):
                    logger.info("signal_already_processed", signal_id=signal_id, status=signal_db.status if signal_db else "not_found")
                    return
                is_exit_signal = signal_db.strategy.startswith("exit_") if signal_db.strategy else False
        except Exception:
            logger.exception("idempotency_check_failed", signal_id=signal_id)
            is_exit_signal = False

        try:
            if is_exit_signal:
                # Çıkış sinyali — mevcut açık trade'i kapat
                await self._execute_exit(signal_id, symbol, side, entry_price)
            else:
                # Giriş sinyali — yeni pozisyon aç
                if not stop_loss:
                    logger.warning("no_stop_loss_skipping", signal_id=signal_id, symbol=symbol)
                    return
                await self._execute_entry(signal_id, symbol, side, entry_price, stop_loss, take_profit, confidence)

            logger.info("signal_executed_successfully", signal_id=signal_id, symbol=symbol, side=side)

            # Sinyal durumunu EXECUTED olarak güncelle
            try:
                async with get_session() as session:
                    repo = SignalRepository(session)
                    await repo.update_status(_uuid.UUID(signal_id), SignalStatus.EXECUTED)
            except Exception:
                logger.exception("signal_status_update_failed", signal_id=signal_id)

        except Exception as e:
            logger.exception("signal_execution_failed", signal_id=signal_id, symbol=symbol, error=str(e))

            # Sinyal durumunu rejected olarak güncelle (tekrar denenmemesi için)
            try:
                async with get_session() as session:
                    repo = SignalRepository(session)
                    await repo.update_status(_uuid.UUID(signal_id), SignalStatus.REJECTED)
            except Exception:
                logger.exception("signal_status_update_failed", signal_id=signal_id)

            # Audit log
            try:
                async with get_session() as session:
                    await log_audit(
                        session,
                        action="execution_failed",
                        entity_type="signal",
                        entity_id=signal_id,
                        user="system",
                        changes={"error": str(e), "symbol": symbol, "side": side},
                    )
            except Exception:
                logger.exception("audit_log_failed", signal_id=signal_id)

            # Telegram bildirim — risk reddi veya hata
            try:
                from src.core.events import publish as _publish
                error_msg = str(e)
                # Kullanıcı dostu hata mesajları
                if "MaxPositionsError" in type(e).__name__ or "maks" in error_msg.lower() or "max" in error_msg.lower():
                    reason = "Maks pozisyon limitine ulaşıldı"
                elif "InsufficientBalance" in type(e).__name__ or "bakiye" in error_msg.lower():
                    reason = "Yetersiz bakiye"
                elif "CooldownActive" in type(e).__name__ or "cooldown" in error_msg.lower():
                    reason = "Bekleme süresi dolmadı"
                elif "DailyLossLimit" in type(e).__name__:
                    reason = "Günlük kayıp limitine ulaşıldı"
                else:
                    reason = error_msg[:100]

                await _publish(
                    "signal:rejected_by_risk",
                    {
                        "signal_id": signal_id,
                        "symbol": symbol,
                        "side": side,
                        "reason": reason,
                    },
                )
            except Exception:
                logger.exception("risk_notification_failed", signal_id=signal_id)

    async def _execute_entry(
        self,
        signal_id: str,
        symbol: str,
        side: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal | None,
        confidence: float,
    ) -> None:
        """Yeni pozisyon aç — risk kontrolü + emir."""
        usdt_bal = await get_usdt_balance()
        balance = usdt_bal["free"]

        position = await self.risk_manager.validate_and_size(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            balance_usdt=balance,
            confidence=confidence,
        )

        await self.order_manager.execute_signal(
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            quantity=position["quantity"],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    async def _execute_exit(
        self,
        signal_id: str,
        symbol: str,
        side: str,
        entry_price: Decimal,
    ) -> None:
        """Mevcut açık pozisyonu kapat — risk kontrolü yok, miktarı trade'den al."""
        import uuid as _uuid
        from src.db.repositories.trade_repo import TradeRepository

        # Açık trade'i bul
        async with get_session() as session:
            trade_repo = TradeRepository(session)
            open_trades = await trade_repo.get_open_trades(symbol=symbol)

        if not open_trades:
            logger.warning("exit_no_open_trade", signal_id=signal_id, symbol=symbol)
            return

        trade = open_trades[0]
        quantity = trade.quantity

        # Wallet'ta yeterli bakiye var mı kontrol et (çift tetiklenme koruması)
        base_asset = symbol.replace("USDT", "")
        if settings.is_sandbox:
            from src.sandbox.wallet import sandbox_wallet
            bal = await sandbox_wallet.get_balance(base_asset)
            if bal["free"] < quantity:
                # Bakiye yok ama trade open — önceki satış trade'i kapatamamış
                # Trade'i mevcut fiyattan kapat (tutarsızlığı çöz)
                logger.warning(
                    "exit_insufficient_balance_closing_trade",
                    signal_id=signal_id,
                    symbol=symbol,
                    trade_id=str(trade.id),
                )
                try:
                    async with get_session() as session:
                        trade_repo = TradeRepository(session)
                        entry_price_f = float(trade.entry_price)
                        exit_price_f = float(entry_price)
                        qty_f = float(quantity)
                        if trade.side == "BUY":
                            pnl = (exit_price_f - entry_price_f) * qty_f
                        else:
                            pnl = (entry_price_f - exit_price_f) * qty_f
                        pnl_pct = (pnl / (entry_price_f * qty_f)) * 100 if entry_price_f else 0
                        # Orphan close — gerçek exit order yok, exit_order_id NULL bırak
                        # (aksi halde JOIN entry sinyalini exit gibi gösterir)
                        await trade_repo.close_trade(
                            trade.id,
                            exit_order_id=None,
                            exit_price=exit_price_f,
                            realized_pnl=round(pnl, 8),
                            realized_pnl_pct=round(pnl_pct, 4),
                            total_commission=float(trade.total_commission or 0),
                        )
                    logger.info("orphan_trade_closed", trade_id=str(trade.id), symbol=symbol)
                except Exception:
                    logger.exception("orphan_trade_close_failed", trade_id=str(trade.id))
                return

        logger.info(
            "executing_exit_order",
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            quantity=float(quantity),
            trade_id=str(trade.id),
        )

        # Emir oluştur (is_exit=True ile yeni trade oluşturmasın)
        result = await self.order_manager.execute_signal(
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            is_exit=True,
        )

        # Mevcut trade'i kapat
        if result.get("order_id") and not result.get("duplicate"):
            try:
                exit_order_id = _uuid.UUID(result["order_id"])
                fill_price = float(result.get("fill_price", entry_price))
                entry_price_f = float(trade.entry_price)

                if trade.side == "BUY":
                    pnl = (fill_price - entry_price_f) * float(quantity)
                else:
                    pnl = (entry_price_f - fill_price) * float(quantity)
                pnl_pct = (pnl / (entry_price_f * float(quantity))) * 100 if entry_price_f else 0

                total_commission = float(trade.total_commission or 0) + float(result.get("commission", 0))

                async with get_session() as session:
                    trade_repo = TradeRepository(session)
                    await trade_repo.close_trade(
                        trade.id,
                        exit_order_id=exit_order_id,
                        exit_price=fill_price,
                        realized_pnl=round(pnl, 8),
                        realized_pnl_pct=round(pnl_pct, 4),
                        total_commission=total_commission,
                    )

                logger.info(
                    "trade_closed",
                    trade_id=str(trade.id),
                    symbol=symbol,
                    pnl=round(pnl, 4),
                    pnl_pct=round(pnl_pct, 2),
                )
            except Exception:
                logger.exception("trade_close_failed", trade_id=str(trade.id), symbol=symbol)

    async def _handle_exit_signal(self, message: dict) -> None:
        """Çıkış sinyalini işle — pozisyonu kapat."""
        try:
            data = json.loads(message["data"])
            trade_id = data["trade_id"]
            symbol = data["symbol"]
            side = data["side"]  # Çıkış yönü (long pozisyon için SELL)
            reason = data.get("reason", "unknown")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("invalid_exit_signal", error=str(e))
            return

        logger.info(
            "processing_exit_signal",
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            reason=reason,
        )

        try:
            import uuid
            from src.db.repositories.trade_repo import TradeRepository
            from src.db.session import get_session

            # Trade bilgisini al
            async with get_session() as session:
                repo = TradeRepository(session)
                trade = await repo.get_by_id(uuid.UUID(trade_id))

            if not trade or trade.status != "open":
                logger.warning("exit_signal_invalid_trade", trade_id=trade_id)
                return

            # Çıkış emri gönder
            result = await self.order_manager.execute_signal(
                signal_id=f"exit_{trade_id[:8]}",
                symbol=symbol,
                side=side,
                quantity=trade.quantity,
                entry_price=trade.entry_price,  # Referans fiyat
            )

            logger.info(
                "exit_signal_executed",
                trade_id=trade_id,
                symbol=symbol,
                reason=reason,
                order_id=result.get("order_id"),
            )

        except Exception as e:
            logger.exception(
                "exit_signal_execution_failed",
                trade_id=trade_id,
                symbol=symbol,
                error=str(e),
            )
