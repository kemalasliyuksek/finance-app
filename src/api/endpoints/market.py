"""Piyasa ve favori coin API endpoint'leri."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user
from src.core.events import get_cache, set_cache
from src.core.logging import get_logger
from src.db.repositories.favorite_repo import FavoriteRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import get_db
from src.schemas.market import (
    FavoriteSymbolRequest,
    FavoritesResponse,
    MarketCoinItem,
    MarketCoinsResponse,
)
from src.screener.filters import (
    is_blacklisted,
    is_leveraged_token,
    is_stablecoin_pair,
    is_usdt_pair,
)

logger = get_logger("market")
router = APIRouter(tags=["market"])

_CACHE_TTL = 60  # 60 saniye
_BINANCE_BASE = "https://api.binance.com"


async def _fetch_24h_tickers() -> list[dict]:
    """Binance /api/v3/ticker/24hr — tüm coinler, parametresiz."""
    url = f"{_BINANCE_BASE}/api/v3/ticker/24hr"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            return await resp.json()


_BATCH_SIZE = 100  # Binance symbols parametre limiti


async def _fetch_window_changes(symbols: list[str], window: str) -> dict[str, float]:
    """Binance /api/v3/ticker?windowSize=X — batch halinde değişim oranı çek."""
    result: dict[str, float] = {}
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(symbols), _BATCH_SIZE):
            batch = symbols[i : i + _BATCH_SIZE]
            symbols_param = "[" + ",".join(f'"{s}"' for s in batch) + "]"
            url = f"{_BINANCE_BASE}/api/v3/ticker"
            params = {"windowSize": window, "symbols": symbols_param}
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    for t in data:
                        result[t["symbol"]] = float(t.get("priceChangePercent", 0))
            except Exception:
                logger.warning("window_ticker_batch_error", window=window, batch_start=i)
    return result


@router.get("/market/coins", response_model=MarketCoinsResponse)
async def get_market_coins(
    window: Literal["1h", "4h", "1d"] = Query(default="1d", description="Değişim penceresi"),
    _user: str = Depends(get_current_active_user),
) -> MarketCoinsResponse:
    """Tüm USDT çiftlerini Binance'den çek, screener sinyalleri ile birleştir."""
    cache_key = f"market:coins:{window}"
    cached = await get_cache(cache_key)
    if cached:
        return MarketCoinsResponse(**cached)

    # 24h ticker → temel veri (fiyat, hacim, high/low, 24h change)
    try:
        tickers = await _fetch_24h_tickers()
    except Exception:
        logger.exception("market_ticker_fetch_error")
        return MarketCoinsResponse(coins=[], total=0)

    coins: list[MarketCoinItem] = []
    for t in tickers:
        symbol = t.get("symbol", "")
        if not is_usdt_pair(symbol):
            continue
        if is_leveraged_token(symbol) or is_stablecoin_pair(symbol) or is_blacklisted(symbol):
            continue
        try:
            coins.append(MarketCoinItem(
                symbol=symbol,
                price=float(t.get("lastPrice", 0)),
                change_pct=float(t.get("priceChangePercent", 0)),
                volume_24h=float(t.get("quoteVolume", 0)),
                high_24h=float(t.get("highPrice", 0)),
                low_24h=float(t.get("lowPrice", 0)),
            ))
        except (ValueError, TypeError):
            continue

    # 1h/4h seçildiyse tüm coinlerin change_pct'sini güncelle (batch, cache'li)
    if window != "1d" and coins:
        all_symbols = [c.symbol for c in coins]
        window_changes = await _fetch_window_changes(all_symbols, window)
        for coin in coins:
            if coin.symbol in window_changes:
                coin.change_pct = window_changes[coin.symbol]

    # Screener sinyalleri ile eşleştir
    screener_data = await get_cache("screener:latest_results")
    if screener_data and screener_data.get("results"):
        signal_map = {r["symbol"]: r for r in screener_data["results"]}
        for coin in coins:
            sig = signal_map.get(coin.symbol)
            if sig:
                coin.has_signal = True
                coin.signal_side = sig.get("side")
                coin.signal_confidence = sig.get("confidence")

    coins.sort(key=lambda c: c.volume_24h, reverse=True)

    now = datetime.now(timezone.utc).isoformat()
    response = MarketCoinsResponse(coins=coins, total=len(coins), cached_at=now)
    await set_cache(cache_key, response.model_dump(), ttl_seconds=_CACHE_TTL)

    logger.info("market_coins_fetched", total=len(coins), window=window)
    return response


# --- Favoriler ---


async def _get_user_id(username: str, db: AsyncSession):
    """Username'den user_id çıkar."""
    user = await UserRepository(db).get_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    return user.id


@router.get("/market/favorites", response_model=FavoritesResponse)
async def get_favorites(
    username: str = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FavoritesResponse:
    """Kullanıcının favori coin listesini getir."""
    user_id = await _get_user_id(username, db)
    symbols = await FavoriteRepository(db).get_symbols_by_user(user_id)
    return FavoritesResponse(favorites=symbols)


@router.post("/market/favorites", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    body: FavoriteSymbolRequest,
    username: str = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Favori coin ekle."""
    user_id = await _get_user_id(username, db)
    symbol = body.symbol.upper()
    result = await FavoriteRepository(db).add(user_id, symbol)
    if result is None:
        return {"status": "already_exists", "symbol": symbol}
    return {"status": "added", "symbol": symbol}


@router.delete("/market/favorites/{symbol}", status_code=status.HTTP_200_OK)
async def remove_favorite(
    symbol: str,
    username: str = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Favori coin sil."""
    user_id = await _get_user_id(username, db)
    removed = await FavoriteRepository(db).remove(user_id, symbol.upper())
    if not removed:
        raise HTTPException(status_code=404, detail="Favori bulunamadı")
    return {"status": "removed", "symbol": symbol.upper()}
