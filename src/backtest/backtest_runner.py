"""Backtesting motoru - tarihsel veri uzerinde strateji testi."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import pandas as pd

from src.analysis.ta_engine import run_analysis
from src.config import settings
from src.constants import BINANCE_FEE_RATE, Side
from src.core.logging import get_logger
from src.strategy.ema_crossover import EMACrossoverStrategy

logger = get_logger("backtest")


@dataclass
class BacktestTrade:
    """Backtesting trade kaydi."""

    entry_idx: int
    exit_idx: int | None = None
    side: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0


@dataclass
class BacktestResult:
    """Backtesting sonucu."""

    trades: list[BacktestTrade] = field(default_factory=list)
    initial_balance: float = 0.0
    final_balance: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    avg_trade_pnl: float = 0.0
    total_commission: float = 0.0
    equity_curve: list[float] = field(default_factory=list)


def run_backtest(
    df: pd.DataFrame,
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    initial_balance: float = 500.0,
    risk_per_trade: float = 0.02,
    slippage_pct: float = 0.0005,  # %0.05
    fee_rate: float = BINANCE_FEE_RATE,
    lookback: int = 50,  # Analiz icin gereken minimum mum sayisi
) -> BacktestResult:
    """Tarihsel veri uzerinde strateji test et.

    Args:
        df: OHLCV DataFrame
        symbol: Trading cifti
        interval: Zaman dilimi
        initial_balance: Baslangic bakiyesi
        risk_per_trade: Trade basina risk orani
        slippage_pct: Tahmini kayma orani
        fee_rate: Komisyon orani
        lookback: Her analiz icin gereken mum sayisi

    Returns:
        BacktestResult
    """
    strategy = EMACrossoverStrategy()
    balance = initial_balance
    trades: list[BacktestTrade] = []
    equity_curve = [balance]
    open_trade: BacktestTrade | None = None

    logger.info(
        "backtest_starting",
        symbol=symbol,
        interval=interval,
        candles=len(df),
        balance=initial_balance,
    )

    for i in range(lookback, len(df)):
        # Analiz penceresi
        window = df.iloc[max(0, i - 200) : i + 1]

        if len(window) < 30:
            equity_curve.append(balance)
            continue

        # Teknik analiz
        ta_result = run_analysis(window, symbol=symbol, interval=interval)

        if not ta_result.current_price:
            equity_curve.append(balance)
            continue

        current_price = ta_result.current_price

        # Acik pozisyon varsa SL/TP kontrolu
        if open_trade:
            sl_hit = False
            tp_hit = False
            exit_price = 0.0

            candle = df.iloc[i]
            high = float(candle["high"])
            low = float(candle["low"])

            if open_trade.side == Side.BUY:
                if low <= open_trade.exit_price:  # SL (exit_price = SL olarak kullaniliyor)
                    # Gercekte SL ve TP ayri tutulmali, burada basitlestirildi
                    pass

            # Basit cikis: ters sinyal geldiginde kapat
            signal = strategy.evaluate(ta_result, sentiment_score=None)

            should_close = False
            if signal and signal.side != open_trade.side:
                should_close = True

            if should_close:
                exit_price = current_price * (1 - slippage_pct if open_trade.side == Side.SELL else 1 + slippage_pct)
                commission = open_trade.quantity * exit_price * fee_rate

                if open_trade.side == Side.BUY:
                    pnl = (exit_price - open_trade.entry_price) * open_trade.quantity - commission - open_trade.commission
                else:
                    pnl = (open_trade.entry_price - exit_price) * open_trade.quantity - commission - open_trade.commission

                pnl_pct = (pnl / (open_trade.entry_price * open_trade.quantity)) * 100

                open_trade.exit_idx = i
                open_trade.exit_price = exit_price
                open_trade.pnl = pnl
                open_trade.pnl_pct = pnl_pct
                open_trade.commission += commission

                balance += pnl
                trades.append(open_trade)
                open_trade = None

        # Yeni sinyal kontrolu (sadece pozisyon yokken)
        if open_trade is None:
            signal = strategy.evaluate(ta_result, sentiment_score=None)

            if signal:
                # Pozisyon boyutlama
                risk_amount = balance * risk_per_trade
                sl_distance = abs(float(signal.entry_price) - float(signal.stop_loss))

                if sl_distance > 0:
                    position_value = risk_amount / (sl_distance / current_price)
                    position_value = min(position_value, balance * 0.4)  # Max %40 allocation
                    quantity = position_value / current_price

                    entry_price = current_price * (1 + slippage_pct if signal.side == Side.BUY else 1 - slippage_pct)
                    commission = quantity * entry_price * fee_rate

                    open_trade = BacktestTrade(
                        entry_idx=i,
                        side=signal.side,
                        entry_price=entry_price,
                        quantity=quantity,
                        commission=commission,
                    )

        equity_curve.append(balance)

    # Acik pozisyonu son fiyattan kapat
    if open_trade:
        exit_price = float(df["close"].iloc[-1])
        commission = open_trade.quantity * exit_price * fee_rate

        if open_trade.side == Side.BUY:
            pnl = (exit_price - open_trade.entry_price) * open_trade.quantity - commission - open_trade.commission
        else:
            pnl = (open_trade.entry_price - exit_price) * open_trade.quantity - commission - open_trade.commission

        open_trade.exit_idx = len(df) - 1
        open_trade.exit_price = exit_price
        open_trade.pnl = pnl
        open_trade.commission += commission
        balance += pnl
        trades.append(open_trade)

    # Sonuclari hesapla
    result = _calculate_results(trades, initial_balance, balance, equity_curve)

    logger.info(
        "backtest_complete",
        total_trades=result.total_trades,
        win_rate=f"{result.win_rate:.1f}%",
        total_pnl=f"{result.total_pnl:.2f}",
        max_drawdown=f"{result.max_drawdown_pct:.1f}%",
        profit_factor=f"{result.profit_factor:.2f}",
    )

    return result


def _calculate_results(
    trades: list[BacktestTrade],
    initial_balance: float,
    final_balance: float,
    equity_curve: list[float],
) -> BacktestResult:
    """Backtest istatistiklerini hesapla."""
    if not trades:
        return BacktestResult(
            initial_balance=initial_balance,
            final_balance=final_balance,
            equity_curve=equity_curve,
        )

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]

    total_pnl = sum(t.pnl for t in trades)
    gross_profit = sum(t.pnl for t in wins) if wins else 0
    gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0

    # Max drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd

    max_dd_pct = (max_dd / initial_balance) * 100 if initial_balance > 0 else 0

    return BacktestResult(
        trades=trades,
        initial_balance=initial_balance,
        final_balance=final_balance,
        total_pnl=total_pnl,
        total_pnl_pct=(total_pnl / initial_balance) * 100 if initial_balance > 0 else 0,
        total_trades=len(trades),
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=(len(wins) / len(trades)) * 100 if trades else 0,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        profit_factor=gross_profit / gross_loss if gross_loss > 0 else 999.0,
        avg_trade_pnl=total_pnl / len(trades) if trades else 0,
        total_commission=sum(t.commission for t in trades),
        equity_curve=equity_curve,
    )
