"""CryptoPanic API client - kripto haber ve sentiment verisi."""

from __future__ import annotations

import httpx

from src.config import settings
from src.core.events import set_cache
from src.core.logging import get_logger

logger = get_logger("cryptopanic")

BASE_URL = "https://cryptopanic.com/api/v1"

# Symbol -> CryptoPanic currency mapping (bilinen çiftler)
SYMBOL_MAP = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "BNBUSDT": "BNB",
    "SOLUSDT": "SOL",
    "XRPUSDT": "XRP",
    "DOGEUSDT": "DOGE",
    "ADAUSDT": "ADA",
    "AVAXUSDT": "AVAX",
}

# Bilinen USDT/BUSD/USDC suffix'leri — dinamik coin desteği için
_QUOTE_SUFFIXES = ("USDT", "BUSD", "USDC", "TUSD", "FDUSD")


def _symbol_to_currency(symbol: str) -> str | None:
    """Trading pair'den CryptoPanic currency kodunu çıkar.

    Önce static map'e bakar, sonra suffix'i kaldırarak fallback yapar.
    """
    if symbol in SYMBOL_MAP:
        return SYMBOL_MAP[symbol]

    # Dinamik: suffix'i kaldır
    for suffix in _QUOTE_SUFFIXES:
        if symbol.endswith(suffix):
            base = symbol[: -len(suffix)]
            if base:  # Boş string kontrolü
                return base
    return None


async def fetch_news(
    currency: str = "BTC",
    kind: str = "news",
    limit: int = 20,
) -> list[dict]:
    """CryptoPanic'ten haber cek.

    Args:
        currency: Kripto kodu (BTC, ETH, vb.)
        kind: Icerik tipi (news, media, all)
        limit: Maks haber sayisi

    Returns:
        Haber listesi
    """
    if not settings.cryptopanic_api_key:
        logger.debug("cryptopanic_api_key_not_set")
        return []

    params = {
        "auth_token": settings.cryptopanic_api_key,
        "currencies": currency,
        "kind": kind,
        "public": "true",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/posts/", params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])[:limit]

            logger.debug(
                "news_fetched",
                currency=currency,
                count=len(results),
            )
            return results
    except httpx.HTTPError:
        logger.exception("cryptopanic_fetch_error", currency=currency)
        return []


async def fetch_and_score(symbol: str) -> dict | None:
    """Symbol icin haber cek ve sentiment skoru hesapla.

    Returns:
        {"score": float, "article_count": int, "bullish": int, "bearish": int}
        veya None
    """
    currency = _symbol_to_currency(symbol)
    if not currency:
        return None

    articles = await fetch_news(currency=currency)
    if not articles:
        return None

    # CryptoPanic vote-based sentiment
    bullish = 0
    bearish = 0
    total = 0

    for article in articles:
        votes = article.get("votes", {})
        b = votes.get("positive", 0) + votes.get("liked", 0)
        bear = votes.get("negative", 0) + votes.get("disliked", 0)
        bullish += b
        bearish += bear
        total += 1

    # Normalize: -1.0 (full bearish) to +1.0 (full bullish)
    total_votes = bullish + bearish
    if total_votes == 0:
        score = 0.0
    else:
        score = (bullish - bearish) / total_votes

    result = {
        "score": round(score, 4),
        "article_count": total,
        "bullish": bullish,
        "bearish": bearish,
    }

    # Redis cache (5 dakika TTL)
    from src.constants import RedisChannel
    await set_cache(RedisChannel.sentiment(symbol), result, ttl_seconds=300)

    logger.info(
        "sentiment_scored",
        symbol=symbol,
        score=score,
        articles=total,
        bullish=bullish,
        bearish=bearish,
    )

    return result
