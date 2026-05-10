"""Strateji base class - tüm stratejiler bunu implemente eder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from src.analysis.ta_engine import TAResult
from src.schemas.signal import SignalCreate


@dataclass
class ExitSignal:
    """Çıkış sinyali — açık pozisyonun kapatılmasını önerir."""

    symbol: str
    side: str  # Çıkış yönü: long pozisyon için SELL, short için BUY
    reason: str  # ema_reverse, stop_loss, take_profit, rsi_extreme
    confidence: float


class BaseStrategy(ABC):
    """Trading stratejisi arayüzü."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strateji adı (DB'ye kaydedilir)."""
        ...

    @abstractmethod
    def evaluate(
        self,
        ta_result: TAResult,
        sentiment_score: float | None = None,
    ) -> SignalCreate | None:
        """Teknik analiz ve sentiment verilerini değerlendir.

        Args:
            ta_result: Teknik analiz sonuçları
            sentiment_score: Haber sentiment skoru (-1.0 ~ 1.0), None ise yok sayılır

        Returns:
            SignalCreate: Al/Sat sinyali veya None (sinyal yok)
        """
        ...

    def evaluate_exit(
        self,
        ta_result: TAResult,
        open_trade: object,
    ) -> ExitSignal | None:
        """Açık pozisyon için çıkış sinyali değerlendir.

        Args:
            ta_result: Güncel teknik analiz sonuçları
            open_trade: Açık trade objesi (symbol, side, entry_price, stop_loss, take_profit)

        Returns:
            ExitSignal veya None (çıkış yok)
        """
        return None  # Alt sınıflar override edebilir
