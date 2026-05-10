"""Piyasa (market) API şemaları."""

from __future__ import annotations

from pydantic import BaseModel


class MarketCoinItem(BaseModel):
    symbol: str
    price: float
    change_pct: float
    volume_24h: float
    high_24h: float
    low_24h: float
    has_signal: bool = False
    signal_side: str | None = None
    signal_confidence: float | None = None


class MarketCoinsResponse(BaseModel):
    coins: list[MarketCoinItem]
    total: int
    cached_at: str | None = None


class FavoriteSymbolRequest(BaseModel):
    symbol: str


class FavoritesResponse(BaseModel):
    favorites: list[str]
