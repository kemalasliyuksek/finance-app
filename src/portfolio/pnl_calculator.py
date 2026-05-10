"""Kar/Zarar hesaplayici."""

from __future__ import annotations

from decimal import Decimal

from src.constants import TradeStatus
from src.core.logging import get_logger
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_session

logger = get_logger("pnl_calculator")


class PnLCalculator:
    """Trade bazli ve portfoy geneli PnL hesaplama."""

    async def get_summary(self, initial_balance: Decimal = Decimal("0")) -> dict:
        """Portfoy PnL ozeti.

        Returns:
            {
                "total_pnl": Decimal,
                "total_pnl_pct": Decimal,
                "total_trades": int,
                "winning_trades": int,
                "losing_trades": int,
                "breakeven_trades": int,
                "win_rate": Decimal,
                "avg_win": Decimal,
                "avg_loss": Decimal,
                "best_trade": Decimal,
                "worst_trade": Decimal,
                "profit_factor": Decimal,
                "total_commission": Decimal,
            }
        """
        async with get_session() as session:
            repo = TradeRepository(session)
            closed_trades = await repo.get_closed_trades(limit=1000)

        if not closed_trades:
            return self._empty_summary()

        total_pnl = Decimal("0")
        total_commission = Decimal("0")
        wins = []
        losses = []

        for trade in closed_trades:
            pnl = trade.realized_pnl or Decimal("0")
            total_pnl += pnl
            total_commission += trade.total_commission or Decimal("0")

            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(pnl)

        total_trades = len(closed_trades)
        winning = len(wins)
        losing = len(losses)
        breakeven = total_trades - winning - losing

        win_rate = Decimal(str(winning / total_trades * 100)) if total_trades > 0 else Decimal("0")
        avg_win = sum(wins) / len(wins) if wins else Decimal("0")
        avg_loss = sum(losses) / len(losses) if losses else Decimal("0")
        best = max(wins) if wins else Decimal("0")
        worst = min(losses) if losses else Decimal("0")

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal("999")

        total_pnl_pct = (
            (total_pnl / initial_balance * 100) if initial_balance > 0 else Decimal("0")
        )

        # Drawdown hesaplama — kümülatif PnL üzerinden
        max_drawdown, max_drawdown_pct = self._calculate_drawdown(
            closed_trades, initial_balance
        )

        return {
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "total_trades": total_trades,
            "winning_trades": winning,
            "losing_trades": losing,
            "breakeven_trades": breakeven,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "best_trade": best,
            "worst_trade": worst,
            "profit_factor": profit_factor,
            "total_commission": total_commission,
            "max_drawdown_usdt": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
        }

    async def get_daily_pnl(self) -> dict:
        """Bugunun PnL ozeti."""
        async with get_session() as session:
            repo = TradeRepository(session)
            today_trades = await repo.get_today_trades()

        daily_pnl = sum(
            (t.realized_pnl or Decimal("0")) for t in today_trades if t.status == TradeStatus.CLOSED
        )
        daily_trades = len(today_trades)
        daily_wins = sum(1 for t in today_trades if (t.realized_pnl or 0) > 0)

        return {
            "daily_pnl": daily_pnl,
            "daily_trades": daily_trades,
            "daily_wins": daily_wins,
            "daily_losses": daily_trades - daily_wins,
        }

    @staticmethod
    def _calculate_drawdown(closed_trades, initial_balance: Decimal) -> tuple[Decimal, Decimal]:
        """Kümülatif PnL üzerinden maksimum drawdown hesapla.

        Returns:
            (max_drawdown_usdt, max_drawdown_pct)
        """
        if not closed_trades:
            return Decimal("0"), Decimal("0")

        # Trade'leri kronolojik sırala
        sorted_trades = sorted(closed_trades, key=lambda t: t.closed_at or t.opened_at)

        cumulative = initial_balance or Decimal("0")
        peak = cumulative
        max_drawdown = Decimal("0")

        for trade in sorted_trades:
            pnl = trade.realized_pnl or Decimal("0")
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdown_pct = (
            (max_drawdown / peak * 100) if peak > 0 else Decimal("0")
        )

        return max_drawdown, max_drawdown_pct

    def _empty_summary(self) -> dict:
        zero = Decimal("0")
        return {
            "total_pnl": zero,
            "total_pnl_pct": zero,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "win_rate": zero,
            "avg_win": zero,
            "avg_loss": zero,
            "best_trade": zero,
            "worst_trade": zero,
            "profit_factor": zero,
            "total_commission": zero,
            "max_drawdown_usdt": zero,
            "max_drawdown_pct": zero,
        }
