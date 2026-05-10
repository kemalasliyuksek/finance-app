"""Uygulama geneli özel exception'lar."""

from __future__ import annotations


class TradingBotError(Exception):
    """Tüm trading bot hatalarının base class'ı."""


class InsufficientBalanceError(TradingBotError):
    """Yetersiz bakiye."""


class RiskLimitExceededError(TradingBotError):
    """Risk limiti aşıldı."""


class DailyLossLimitError(RiskLimitExceededError):
    """Günlük kayıp limiti aşıldı."""


class MaxPositionsError(RiskLimitExceededError):
    """Maksimum pozisyon limiti aşıldı."""


class CooldownActiveError(RiskLimitExceededError):
    """Cooldown süresi devam ediyor."""


class OrderExecutionError(TradingBotError):
    """Emir gönderme/işleme hatası."""


class BinanceAPIError(TradingBotError):
    """Binance API hatası."""


class SignalExpiredError(TradingBotError):
    """Sinyal süresi dolmuş."""


class ConfigurationError(TradingBotError):
    """Konfigürasyon hatası."""
