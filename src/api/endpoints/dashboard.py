"""Dashboard özet endpoint'i."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user
from src.config import settings
from src.core.events import get_cache
from src.core.logging import get_logger
from src.db.repositories.portfolio_repo import PortfolioRepository
from src.db.repositories.signal_repo import SignalRepository
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_db
from src.schemas.dashboard import DashboardSummary
from src.schemas.signal import SignalRead

logger = get_logger("dashboard")
router = APIRouter(tags=["dashboard"])


async def _get_price_map() -> dict[str, float]:
    """Market cache'den fiyat haritası oluştur. Cache boşsa screener cache'i dene."""
    # Market coins cache (60s TTL)
    for suffix in (":1d", ":4h", ":1h"):
        data = await get_cache(f"market:coins{suffix}")
        if data and data.get("coins"):
            return {c["symbol"]: c["price"] for c in data["coins"]}

    # Fallback: screener cache (5dk TTL, daha uzun ömürlü)
    screener = await get_cache("screener:latest_results")
    if screener and screener.get("results"):
        return {r["symbol"]: r["price"] for r in screener["results"]}

    return {}


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> DashboardSummary:
    """Ana dashboard özet verisi."""
    portfolio_repo = PortfolioRepository(db)
    trade_repo = TradeRepository(db)
    signal_repo = SignalRepository(db)

    today_trades = await trade_repo.get_today_trades()
    open_count = await trade_repo.count_open()
    recent_signals = await signal_repo.get_recent(limit=5)

    today_pnl = sum(
        (t.realized_pnl or Decimal("0")) for t in today_trades if t.realized_pnl
    )
    closed_today = [t for t in today_trades if t.realized_pnl is not None]
    winning = sum(1 for t in closed_today if t.realized_pnl and t.realized_pnl > 0)
    win_rate = (
        Decimal(winning) / Decimal(len(closed_today)) if closed_today else Decimal("0")
    )

    # Fiyat haritası — toplam bakiye ve unrealized PnL için
    price_map = await _get_price_map()

    # Unrealized PnL: açık trade'ler için güncel fiyat üzerinden hesapla
    unrealized_pnl = Decimal("0")
    open_trades = await trade_repo.get_open_trades()
    if open_trades and price_map:
        for t in open_trades:
            current = price_map.get(t.symbol)
            if current and t.entry_price and t.quantity:
                ep = float(t.entry_price)
                qty = float(t.quantity)
                if t.side == "BUY":
                    unrealized_pnl += Decimal(str(round((current - ep) * qty, 8)))
                else:
                    unrealized_pnl += Decimal(str(round((ep - current) * qty, 8)))

    # Bakiye: sandbox modda cüzdandan, live modda snapshot'tan
    if settings.is_sandbox:
        from src.sandbox.wallet import sandbox_wallet
        usdt_bal = await sandbox_wallet.get_usdt_balance()
        free_balance = usdt_bal["free"]

        # Toplam bakiye = USDT + wallet'taki tüm coin'lerin güncel USDT değeri
        all_balances = await sandbox_wallet.get_account_balance()
        positions_value = Decimal("0")
        for asset, amount in all_balances.items():
            if asset == "USDT" or float(amount) == 0:
                continue
            symbol = f"{asset}USDT"
            current = price_map.get(symbol)
            if current:
                positions_value += Decimal(str(round(current * float(amount), 8)))
            else:
                logger.debug("price_not_found_for_asset", asset=asset, symbol=symbol)

        total_balance = usdt_bal["total"] + positions_value
    else:
        snapshot = await portfolio_repo.get_latest()
        total_balance = snapshot.total_balance_usdt if snapshot else Decimal("0")
        free_balance = snapshot.free_balance_usdt if snapshot else Decimal("0")

    return DashboardSummary(
        total_balance_usdt=total_balance,
        free_balance_usdt=free_balance,
        unrealized_pnl=unrealized_pnl,
        open_positions=open_count,
        today_pnl=today_pnl,
        today_trades_count=len(today_trades),
        win_rate=win_rate,
        recent_signals=[SignalRead.model_validate(s) for s in recent_signals],
        app_mode=settings.app_mode,
        trading_mode=settings.trading_mode,
        active_pairs=settings.trading_pairs,
        is_sandbox=settings.is_sandbox,
    )
