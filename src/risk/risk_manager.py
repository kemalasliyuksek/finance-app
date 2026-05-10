"""Risk yonetimi - her sinyal bu kapidan gecmek zorunda."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.config import settings
from src.constants import Side, TradeStatus
from src.core.exceptions import (
    CooldownActiveError,
    DailyLossLimitError,
    InsufficientBalanceError,
    MaxPositionsError,
    RiskLimitExceededError,
)
from src.core.logging import get_logger
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_session
from src.risk.position_sizer import calculate_position_size

logger = get_logger("risk_manager")


class RiskManager:
    """Her sinyal bu risk kontrollerinden gecmek zorunda."""

    def __init__(self) -> None:
        self._last_trade_times: dict[str, datetime] = {}  # symbol → son entry zamanı
        self._lock = asyncio.Lock()

    async def validate_and_size(
        self,
        symbol: str,
        side: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        balance_usdt: Decimal,
        confidence: float,
    ) -> dict:
        """Sinyal icin tum risk kontrollerini yap ve pozisyon boyutla.

        Args:
            symbol: Trading cifti
            side: BUY/SELL
            entry_price: Giris fiyati
            stop_loss: Stop-loss fiyati
            balance_usdt: Mevcut bakiye
            confidence: Sinyal guven skoru

        Returns:
            Position sizing sonucu (quantity, risk_usdt, vb.)

        Raises:
            RiskLimitExceededError alt siniflari
        """
        async with self._lock:
            # 1) Minimum bakiye kontrolu
            self._check_min_balance(balance_usdt)

            # 2) Gunluk kayip limiti
            await self._check_daily_loss_limit(balance_usdt)

            # 3) Maksimum pozisyon sayisi
            await self._check_max_positions()

            # 4) Cooldown kontrolu (coin bazli)
            self._check_cooldown(symbol)

            # 5) Gunluk trade limiti
            await self._check_daily_trade_limit()

            # 6) Pozisyon boyutlama
            position = calculate_position_size(
                balance_usdt=balance_usdt,
                entry_price=entry_price,
                stop_loss=stop_loss,
                side=side,
            )

            # 7) Son trade zamanini guncelle (coin bazli)
            self._last_trade_times[symbol] = datetime.now(timezone.utc)

        logger.info(
            "risk_check_passed",
            symbol=symbol,
            side=side,
            quantity=float(position["quantity"]),
            risk_usdt=float(position["risk_usdt"]),
        )

        return position

    def _check_min_balance(self, balance: Decimal) -> None:
        """Minimum bakiye kontrolu."""
        min_bal = Decimal(str(settings.min_balance_usdt))
        if balance < min_bal:
            raise InsufficientBalanceError(
                f"Bakiye ({balance} USDT) minimum limitin ({min_bal} USDT) altinda. "
                "Trading durduruldu."
            )

    async def _check_daily_loss_limit(self, balance: Decimal) -> None:
        """Gunluk kayip limiti kontrolu."""
        async with get_session() as session:
            repo = TradeRepository(session)
            today_trades = await repo.get_today_trades()

        daily_loss = sum(
            float(t.realized_pnl)
            for t in today_trades
            if t.realized_pnl and float(t.realized_pnl) < 0
        )

        max_daily_loss = float(balance) * settings.daily_loss_limit_pct

        if abs(daily_loss) >= max_daily_loss:
            raise DailyLossLimitError(
                f"Gunluk kayip limiti asildi: {abs(daily_loss):.2f} USDT >= "
                f"{max_daily_loss:.2f} USDT ({settings.daily_loss_limit_pct*100:.1f}%)"
            )

    async def _check_max_positions(self) -> None:
        """Maksimum esanli pozisyon kontrolu."""
        async with get_session() as session:
            repo = TradeRepository(session)
            open_count = await repo.count_open()

        if open_count >= settings.max_concurrent_positions:
            raise MaxPositionsError(
                f"Maksimum pozisyon limiti ({settings.max_concurrent_positions}) doldu. "
                f"Acik pozisyon: {open_count}"
            )

    def _check_cooldown(self, symbol: str) -> None:
        """Coin bazli bekleme suresi kontrolu.

        Sadece ayni coin icin gecerli — farkli coinlerde cooldown uygulanmaz.
        Exit emirleri cooldown tetiklemez (validate_and_size sadece entry icin cagrilir).
        """
        last_time = self._last_trade_times.get(symbol)
        if last_time is None:
            return

        elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
        if elapsed < settings.cooldown_seconds:
            remaining = settings.cooldown_seconds - elapsed
            raise CooldownActiveError(
                f"Cooldown aktif ({symbol}). Kalan sure: {remaining:.0f} saniye"
            )

    async def _check_daily_trade_limit(self) -> None:
        """Gunluk trade sayisi limiti kontrolu."""
        async with get_session() as session:
            repo = TradeRepository(session)
            today_trades = await repo.get_today_trades()

        if len(today_trades) >= settings.max_trades_per_day:
            raise RiskLimitExceededError(
                f"Gunluk trade limiti ({settings.max_trades_per_day}) doldu."
            )
