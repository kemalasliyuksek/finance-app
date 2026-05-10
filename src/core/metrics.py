"""Prometheus metrikleri - mevcut Grafana/Prometheus stack ile entegre."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# --- Counter'lar ---
signals_total = Counter(
    "trading_signals_total",
    "Toplam sinyal sayısı",
    ["symbol", "side", "strategy", "status"],
)

orders_total = Counter(
    "trading_orders_total",
    "Toplam emir sayısı",
    ["symbol", "side", "type", "status"],
)

trades_total = Counter(
    "trading_trades_total",
    "Toplam trade sayısı",
    ["symbol", "side", "result"],  # win / loss / breakeven
)

# --- Gauge'lar ---
balance_usdt = Gauge(
    "trading_balance_usdt",
    "Mevcut USDT bakiye",
)

unrealized_pnl_usdt = Gauge(
    "trading_unrealized_pnl_usdt",
    "Gerçekleşmemiş kar/zarar (USDT)",
)

open_positions_count = Gauge(
    "trading_open_positions_count",
    "Açık pozisyon sayısı",
)

daily_loss_usdt = Gauge(
    "trading_daily_loss_usdt",
    "Günlük gerçekleşmiş kayıp (USDT)",
)

daily_loss_remaining_usdt = Gauge(
    "trading_daily_loss_remaining_usdt",
    "Günlük kalan kayıp limiti (USDT)",
)

# --- Histogram'lar ---
signal_confidence = Histogram(
    "trading_signal_confidence",
    "Sinyal güven skoru dağılımı",
    ["strategy"],
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

order_latency_seconds = Histogram(
    "trading_order_latency_seconds",
    "Emir işlem süresi (saniye)",
    ["operation"],  # submit / fill
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

signal_latency_seconds = Histogram(
    "trading_signal_latency_seconds",
    "Sinyal üretim süresi (mum kapanışından sinyale)",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

api_latency_seconds = Histogram(
    "trading_api_latency_seconds",
    "Binance API yanıt süresi",
    ["endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

trade_pnl_usdt = Histogram(
    "trading_trade_pnl_usdt",
    "Trade kar/zarar dağılımı (USDT)",
    ["symbol"],
    buckets=[-50, -20, -10, -5, -2, -1, 0, 1, 2, 5, 10, 20, 50],
)

trade_duration_seconds = Histogram(
    "trading_trade_duration_seconds",
    "Trade süre dağılımı",
    ["symbol"],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400, 28800, 86400],
)
