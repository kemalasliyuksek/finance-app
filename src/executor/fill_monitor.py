"""Emir fill monitor - Binance user data stream ile anlik takip."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from binance import AsyncClient, BinanceSocketManager

from src.constants import OrderStatus, TradeStatus
from src.core.events import publish
from src.core.logging import get_logger
from src.core.metrics import trades_total, trade_pnl_usdt, trade_duration_seconds
from src.db.repositories.order_repo import OrderRepository
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_session

logger = get_logger("fill_monitor")


class FillMonitor:
    """Binance user data stream ile emir fill'lerini anlik takip eder."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self._running = False

    async def start(self) -> None:
        """User data stream'i baslat."""
        self._running = True
        bsm = BinanceSocketManager(self.client)

        while self._running:
            try:
                async with bsm.user_socket() as stream:
                    logger.info("user_data_stream_connected")
                    async for msg in stream:
                        if not self._running:
                            break
                        await self._process_message(msg)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("user_data_stream_error")
                if self._running:
                    await asyncio.sleep(5)

    async def stop(self) -> None:
        self._running = False

    async def _process_message(self, msg: dict) -> None:
        """User data stream mesajini isle."""
        event_type = msg.get("e")

        if event_type == "executionReport":
            await self._handle_execution_report(msg)
        elif event_type == "outboundAccountPosition":
            # Bakiye degisikligi - portfolio worker'a bildir
            logger.debug("account_position_update")

    async def _handle_execution_report(self, msg: dict) -> None:
        """Emir yurutme raporunu isle."""
        order_id = msg.get("i")  # Binance order ID
        client_oid = msg.get("C") or msg.get("c")  # Client order ID
        status = msg.get("X")  # Order status
        side = msg.get("S")  # BUY/SELL
        symbol = msg.get("s")
        exec_type = msg.get("x")  # Execution type

        logger.info(
            "execution_report",
            binance_order_id=order_id,
            client_oid=client_oid,
            status=status,
            exec_type=exec_type,
            symbol=symbol,
            side=side,
        )

        if status == "FILLED" and exec_type == "TRADE":
            fill_price = Decimal(msg.get("L", "0"))  # Last fill price
            fill_qty = Decimal(msg.get("l", "0"))  # Last fill quantity
            commission = Decimal(msg.get("n", "0"))  # Commission
            commission_asset = msg.get("N")  # Commission asset

            # DB guncelle
            try:
                async with get_session() as session:
                    order_repo = OrderRepository(session)

                    if client_oid:
                        order = await order_repo.get_by_client_oid(client_oid)
                    else:
                        order = None

                    if order:
                        await order_repo.update_fill(
                            order.id,
                            binance_order_id=order_id,
                            status=OrderStatus.FILLED,
                            filled_quantity=float(fill_qty),
                            avg_fill_price=float(fill_price),
                            commission=float(commission),
                            commission_asset=commission_asset,
                        )

                        # Event yayinla
                        await publish(
                            "order:filled",
                            {
                                "order_id": str(order.id),
                                "signal_id": str(order.signal_id) if order.signal_id else None,
                                "symbol": symbol,
                                "side": side,
                                "fill_price": float(fill_price),
                                "fill_qty": float(fill_qty),
                            },
                        )
            except Exception:
                logger.exception("fill_update_error", binance_order_id=order_id)
