"""Bakiye takibi - hesap bakiyesini periyodik olarak sorgular ve snapshot oluşturur."""

from __future__ import annotations

from decimal import Decimal

from src.config import settings
from src.core.events import get_cache
from src.core.logging import get_logger
from src.core.metrics import balance_usdt, open_positions_count, unrealized_pnl_usdt
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_session
from src.models.portfolio_snapshot import PortfolioSnapshot

logger = get_logger("balance_tracker")


class BalanceTracker:
    """Bakiye ve portfolio snapshot yönetimi."""

    async def take_snapshot(self) -> PortfolioSnapshot:
        """Mevcut hesap durumunun snapshot'ını al ve DB'ye kaydet."""
        if settings.is_sandbox:
            return await self._take_sandbox_snapshot()
        return await self._take_live_snapshot()

    async def _take_sandbox_snapshot(self) -> PortfolioSnapshot:
        """Sandbox modda sanal cüzdandan snapshot oluştur."""
        from src.sandbox.wallet import sandbox_wallet

        usdt = await sandbox_wallet.get_usdt_balance()
        all_balances = await sandbox_wallet.get_account_balance()

        async with get_session() as session:
            trade_repo = TradeRepository(session)
            open_trades = await trade_repo.get_open_trades()
            open_count = len(open_trades)

        # Unrealized PnL ve pozisyon değeri — market cache'den fiyat al
        unrealized = Decimal("0")
        positions_value = Decimal("0")
        price_map = await self._get_price_map()

        # Açık trade'ler için unrealized PnL
        if open_trades and price_map:
            for t in open_trades:
                current = price_map.get(t.symbol)
                if current and t.entry_price and t.quantity:
                    ep = float(t.entry_price)
                    qty = float(t.quantity)
                    if t.side == "BUY":
                        unrealized += Decimal(str(round((current - ep) * qty, 8)))
                    else:
                        unrealized += Decimal(str(round((ep - current) * qty, 8)))

        # Tüm coin bakiyelerinin USDT değeri (wallet'taki her şey)
        if price_map:
            for asset, amount in all_balances.items():
                if asset == "USDT" or float(amount) == 0:
                    continue
                symbol = f"{asset}USDT"
                current = price_map.get(symbol)
                if current:
                    positions_value += Decimal(str(round(current * float(amount), 8)))

        total_balance = usdt["total"] + positions_value
        breakdown = {asset: str(amount) for asset, amount in all_balances.items()}

        snapshot = PortfolioSnapshot(
            total_balance_usdt=total_balance,
            free_balance_usdt=usdt["free"],
            locked_balance_usdt=usdt["locked"],
            unrealized_pnl=unrealized,
            open_positions=open_count,
            asset_breakdown=breakdown,
        )

        async with get_session() as session:
            session.add(snapshot)
            await session.flush()

        balance_usdt.set(float(total_balance))
        open_positions_count.set(open_count)
        unrealized_pnl_usdt.set(float(unrealized))

        logger.info(
            "snapshot_taken",
            balance=float(total_balance),
            free=float(usdt["free"]),
            unrealized_pnl=float(unrealized),
            open_positions=open_count,
            mode="sandbox",
        )
        return snapshot

    async def _take_live_snapshot(self) -> PortfolioSnapshot:
        """Live modda Binance hesabından snapshot oluştur."""
        from src.executor.binance_client import get_account_balance, get_usdt_balance

        usdt = await get_usdt_balance()
        all_balances = await get_account_balance()

        async with get_session() as session:
            trade_repo = TradeRepository(session)
            open_trades = await trade_repo.get_open_trades()
            open_count = len(open_trades)

        unrealized = Decimal("0")
        price_map = await self._get_price_map()

        if open_trades and price_map:
            for t in open_trades:
                current = price_map.get(t.symbol)
                if current and t.entry_price and t.quantity:
                    ep = float(t.entry_price)
                    qty = float(t.quantity)
                    if t.side == "BUY":
                        unrealized += Decimal(str(round((current - ep) * qty, 8)))
                    else:
                        unrealized += Decimal(str(round((ep - current) * qty, 8)))

        breakdown = {asset: str(amount) for asset, amount in all_balances.items()}

        snapshot = PortfolioSnapshot(
            total_balance_usdt=usdt["total"],
            free_balance_usdt=usdt["free"],
            locked_balance_usdt=usdt["locked"],
            unrealized_pnl=unrealized,
            open_positions=open_count,
            asset_breakdown=breakdown,
        )

        async with get_session() as session:
            session.add(snapshot)
            await session.flush()

        balance_usdt.set(float(usdt["total"]))
        open_positions_count.set(open_count)
        unrealized_pnl_usdt.set(float(unrealized))

        logger.info(
            "snapshot_taken",
            balance=float(usdt["total"]),
            free=float(usdt["free"]),
            unrealized_pnl=float(unrealized),
            open_positions=open_count,
            mode="live",
        )
        return snapshot

    @staticmethod
    async def _get_price_map() -> dict[str, float]:
        """Market cache'den fiyat haritası oluştur."""
        for suffix in (":1d", ":4h", ":1h"):
            data = await get_cache(f"market:coins{suffix}")
            if data and data.get("coins"):
                return {c["symbol"]: c["price"] for c in data["coins"]}
        return {}
