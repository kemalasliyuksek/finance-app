"""Binance ham verisini iç Pydantic şemalarına dönüştürür."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from src.schemas.candle import CandleCreate


def normalize_kline(raw: dict, symbol: str, interval: str) -> CandleCreate:
    """Binance kline (REST veya WebSocket) verisini CandleCreate'e dönüştür.

    REST format: liste [open_time, open, high, low, close, volume, close_time, ...]
    WebSocket format: {"k": {"t": ..., "o": ..., "h": ..., ...}}
    """
    if "k" in raw:
        # WebSocket kline format
        k = raw["k"]
        return CandleCreate(
            symbol=symbol,
            interval=interval,
            open_time=_ms_to_dt(k["t"]),
            close_time=_ms_to_dt(k["T"]),
            open=Decimal(str(k["o"])),
            high=Decimal(str(k["h"])),
            low=Decimal(str(k["l"])),
            close=Decimal(str(k["c"])),
            volume=Decimal(str(k["v"])),
            quote_volume=Decimal(str(k["q"])),
            trade_count=int(k["n"]),
        )
    elif isinstance(raw, list):
        # REST kline format: [open_time, O, H, L, C, vol, close_time, quote_vol, trades, ...]
        return CandleCreate(
            symbol=symbol,
            interval=interval,
            open_time=_ms_to_dt(raw[0]),
            close_time=_ms_to_dt(raw[6]),
            open=Decimal(str(raw[1])),
            high=Decimal(str(raw[2])),
            low=Decimal(str(raw[3])),
            close=Decimal(str(raw[4])),
            volume=Decimal(str(raw[5])),
            quote_volume=Decimal(str(raw[7])),
            trade_count=int(raw[8]),
        )
    else:
        raise ValueError(f"Bilinmeyen kline formatı: {type(raw)}")


def normalize_klines_batch(
    raw_list: list, symbol: str, interval: str
) -> list[CandleCreate]:
    """Toplu REST kline verisini dönüştür."""
    return [normalize_kline(raw, symbol, interval) for raw in raw_list]


def _ms_to_dt(ms: int) -> datetime:
    """Milisaniye epoch'u UTC datetime'a çevir."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
