"""Sentiment endpoint'leri."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user
from src.core.events import get_cache
from src.db.session import get_db

router = APIRouter(tags=["sentiment"])


class SentimentResponse(BaseModel):
    symbol: str
    score: float | None
    article_count: int
    source: str
    scored_at: str | None


@router.get("/{symbol}", response_model=SentimentResponse)
async def get_sentiment(
    symbol: str,
    _user: str = Depends(get_current_active_user),
) -> SentimentResponse:
    """Son sentiment skoru (Redis cache'den)."""
    symbol = symbol.upper()
    cached = await get_cache(f"sentiment:{symbol}")
    if cached:
        return SentimentResponse(
            symbol=symbol,
            score=cached.get("score"),
            article_count=cached.get("article_count", 0),
            source=cached.get("source", "cryptopanic"),
            scored_at=cached.get("scored_at"),
        )
    return SentimentResponse(
        symbol=symbol,
        score=None,
        article_count=0,
        source="cryptopanic",
        scored_at=None,
    )
