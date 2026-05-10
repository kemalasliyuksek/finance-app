"""Enum'lar ve sabit değerler."""

from __future__ import annotations

from enum import StrEnum


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class SignalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"
    WEAK = "weak"


class OrderStatus(StrEnum):
    NEW = "new"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    OCO = "OCO"


class TradeStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class AppMode(StrEnum):
    LIVE = "live"
    SANDBOX = "sandbox"
    TESTNET = "testnet"
    BACKTEST = "backtest"


class TradingMode(StrEnum):
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


# Redis kanal isimleri
class RedisChannel:
    CANDLE_CLOSED = "candle:closed:{symbol}:{interval}"
    SIGNAL_NEW = "signal:new"
    ORDER_FILLED = "order:filled"
    SENTIMENT = "sentiment:{symbol}"

    SCREENER_RESULTS = "screener:results"
    SCREENER_STATUS = "screener:status"
    CONFIG_PAIRS_UPDATED = "config:pairs_updated"

    @classmethod
    def candle_closed(cls, symbol: str, interval: str) -> str:
        return cls.CANDLE_CLOSED.format(symbol=symbol, interval=interval)

    @classmethod
    def sentiment(cls, symbol: str) -> str:
        return cls.SENTIMENT.format(symbol=symbol)


# Binance minimum notional — Binance gerçek minimum 5 USDT
# Ancak küçük pozisyonlarda komisyon burn oranı yüksek (16 trade sample'da %56).
# Bu yüzden uygulama seviyesinde 20 USDT zorluyoruz — komisyonun brüt PnL'yi yemesini engeller.
MIN_NOTIONAL_USDT = 20.0

# Binance komisyon oranı
BINANCE_FEE_RATE = 0.001  # %0.1
BINANCE_BNB_FEE_RATE = 0.00075  # %0.075 (BNB ile)
