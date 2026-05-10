"""Mum verisi endpoint'leri."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user
from src.db.repositories.candle_repo import CandleRepository
from src.db.session import get_db
from src.schemas.candle import CandleRead

router = APIRouter(tags=["candles"])


@router.get("/{symbol}/{interval}", response_model=list[CandleRead])
async def list_candles(
    symbol: str,
    interval: str,
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> list[CandleRead]:
    """Son N mum verisi (eskiden yeniye)."""
    repo = CandleRepository(db)
    candles = await repo.get_recent(symbol.upper(), interval, limit=limit)
    return [CandleRead.model_validate(c) for c in candles]


@router.get("/{symbol}/{interval}/range", response_model=list[CandleRead])
async def candles_range(
    symbol: str,
    interval: str,
    start: datetime = Query(...),
    end: datetime = Query(...),
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> list[CandleRead]:
    """Belirli zaman aralığındaki mum verileri (limit korumalı)."""
    repo = CandleRepository(db)
    candles = await repo.get_range(symbol.upper(), interval, start, end, limit=limit)
    return [CandleRead.model_validate(c) for c in candles]
