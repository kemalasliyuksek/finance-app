"""Emir yönetici - sinyal -> emir dönüşümü ve takibi."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from src.config import settings
from src.constants import OrderStatus, OrderType, Side, TradeStatus
from src.core.audit import log_audit
from src.core.events import publish
from src.core.exceptions import OrderExecutionError
from src.core.logging import get_logger
from src.core.metrics import orders_total
from src.db.repositories.order_repo import OrderRepository
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_session
from src.executor.binance_client import place_market_order
from src.models.trade import Trade
from src.schemas.order import OrderCreate

logger = get_logger("order_manager")


class OrderManager:
    """Sinyal onaylandığında emir oluşturur ve yönetir."""

    async def execute_signal(
        self,
        signal_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        is_exit: bool = False,
    ) -> dict:
        """Onaylanmış sinyali emir olarak çalıştır.

        Atomik transaction: order oluşturma, Binance gönderme ve trade
        oluşturma tek session içinde yapılır. Hata olursa tamamı rollback.

        Returns:
            {"order_id": str, "trade_id": str, "binance_order_id": int}
        """
        # Sabit idempotency key — aynı sinyal için tekrar denemede aynı key
        client_oid = f"sig_{signal_id[:16]}"

        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                trade_repo = TradeRepository(session)

                # Daha önce aynı sinyal için emir var mı?
                existing = await order_repo.get_by_client_oid(client_oid)
                if existing:
                    logger.warning(
                        "duplicate_order_skipped",
                        signal_id=signal_id,
                        client_oid=client_oid,
                    )
                    return {"order_id": str(existing.id), "duplicate": True}

                # 1) DB'ye emir kaydet (flush ile ID al, henüz commit yok)
                order_create = OrderCreate(
                    signal_id=uuid.UUID(signal_id),
                    symbol=symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    quantity=quantity,
                    price=entry_price,
                )
                db_order = await order_repo.create(order_create, client_oid=client_oid)
                await session.flush()

                # Audit: emir oluşturuldu
                await log_audit(
                    session,
                    action="order_created",
                    entity_type="order",
                    entity_id=str(db_order.id),
                    changes={"signal_id": signal_id, "symbol": symbol, "side": side, "quantity": float(quantity)},
                )

                # 2) Binance'e gönder (hata olursa session rollback yapacak)
                if settings.is_sandbox:
                    from src.sandbox.executor import sandbox_place_market_order
                    binance_result = await sandbox_place_market_order(
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        entry_price=entry_price,
                        client_order_id=client_oid,
                    )
                else:
                    binance_result = await place_market_order(
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        client_order_id=client_oid,
                    )

                binance_order_id = binance_result.get("orderId")
                fill_price = self._extract_fill_price(binance_result)
                fill_qty = Decimal(binance_result.get("executedQty", "0"))
                commission = self._extract_commission(binance_result)

                # 3) Fill durumunu belirle (kısmi dolum desteği)
                order_status = self._determine_fill_status(fill_qty, quantity)

                # 4) Order güncelle (aynı session)
                await order_repo.update_fill(
                    db_order.id,
                    binance_order_id=binance_order_id,
                    status=order_status,
                    filled_quantity=float(fill_qty),
                    avg_fill_price=float(fill_price) if fill_price else None,
                    commission=float(commission),
                )

                # Audit: emir dolduruldu
                await log_audit(
                    session,
                    action="order_filled",
                    entity_type="order",
                    entity_id=str(db_order.id),
                    changes={
                        "status": order_status,
                        "fill_price": float(fill_price) if fill_price else None,
                        "fill_qty": float(fill_qty),
                        "commission": float(commission),
                    },
                )

                # 5) Trade oluştur (fill > 0, sadece giriş emirleri için)
                trade = None
                if fill_qty > 0 and not is_exit:
                    trade = Trade(
                        symbol=symbol,
                        entry_order_id=db_order.id,
                        side=side,
                        entry_price=fill_price or entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        quantity=fill_qty,
                        status=TradeStatus.OPEN,
                        opened_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        total_commission=commission,
                    )
                    await trade_repo.create(trade)

                    # Audit: trade açıldı
                    await log_audit(
                        session,
                        action="trade_opened",
                        entity_type="trade",
                        entity_id=str(trade.id),
                        changes={
                            "signal_id": signal_id,
                            "order_id": str(db_order.id),
                            "symbol": symbol,
                            "side": side,
                            "entry_price": float(fill_price or entry_price),
                            "quantity": float(fill_qty),
                        },
                    )

                # → session çıkışında tek commit (order + fill + trade atomik)

            # Metrikler (commit sonrası)
            status_label = "filled" if order_status == OrderStatus.FILLED else "partial"
            orders_total.labels(
                symbol=symbol,
                side=side,
                type="MARKET",
                status=status_label,
            ).inc()

            if order_status == OrderStatus.PARTIALLY_FILLED:
                logger.warning(
                    "partial_fill_detected",
                    signal_id=signal_id,
                    order_id=str(db_order.id),
                    requested_qty=float(quantity),
                    filled_qty=float(fill_qty),
                    remaining=float(quantity - fill_qty),
                )

            logger.info(
                "order_executed",
                signal_id=signal_id,
                order_id=str(db_order.id),
                binance_order_id=binance_order_id,
                fill_price=float(fill_price) if fill_price else None,
                fill_qty=float(fill_qty),
                status=order_status,
            )

            # WebSocket bildirimi
            await publish(
                "order:executed",
                {
                    "order_id": str(db_order.id),
                    "signal_id": signal_id,
                    "symbol": symbol,
                    "side": side,
                    "quantity": float(fill_qty or quantity),
                    "price": float(fill_price or entry_price),
                    "order_type": "MARKET",
                    "status": order_status,
                },
            )

            result = {
                "order_id": str(db_order.id),
                "binance_order_id": binance_order_id,
                "status": order_status,
                "fill_price": float(fill_price) if fill_price else None,
                "commission": float(commission),
            }
            if trade:
                result["trade_id"] = str(trade.id)
            return result

        except Exception as e:
            orders_total.labels(
                symbol=symbol, side=side, type="MARKET", status="error"
            ).inc()

            logger.exception("order_execution_failed", signal_id=signal_id)
            raise OrderExecutionError(f"Emir çalıştırma hatası: {e}") from e

    @staticmethod
    def _determine_fill_status(fill_qty: Decimal, requested_qty: Decimal) -> str:
        """Binance fill miktarına göre emir durumunu belirle."""
        if fill_qty >= requested_qty:
            return OrderStatus.FILLED
        if fill_qty > 0:
            return OrderStatus.PARTIALLY_FILLED
        return OrderStatus.NEW

    def _extract_fill_price(self, result: dict) -> Decimal | None:
        """Binance sonucundan ortalama fill fiyatı çıkar."""
        fills = result.get("fills", [])
        if not fills:
            return None

        total_qty = Decimal("0")
        total_cost = Decimal("0")
        for fill in fills:
            qty = Decimal(fill["qty"])
            price = Decimal(fill["price"])
            total_qty += qty
            total_cost += qty * price

        if total_qty > 0:
            return total_cost / total_qty
        return None

    def _extract_commission(self, result: dict) -> Decimal:
        """Binance sonucundan toplam komisyonu çıkar."""
        fills = result.get("fills", [])
        total_commission = Decimal("0")
        for fill in fills:
            total_commission += Decimal(fill.get("commission", "0"))
        return total_commission
