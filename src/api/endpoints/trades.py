"""Trade endpoint'leri."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user
from src.constants import TradeStatus
from src.db.repositories.trade_repo import TradeRepository
from src.db.session import get_db
from src.schemas.pagination import PaginatedResponse
from src.schemas.trade import TradeRead

router = APIRouter(tags=["trades"])


class TradeStats(Decimal):
    pass


from pydantic import BaseModel


class TradeStatsResponse(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    total_pnl: Decimal
    avg_pnl: Decimal
    best_trade_pnl: Decimal
    worst_trade_pnl: Decimal


@router.get("", response_model=PaginatedResponse[TradeRead])
async def list_trades(
    status_filter: TradeStatus | None = Query(None, alias="status"),
    symbol: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None, pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> PaginatedResponse[TradeRead]:
    """Filtrelenebilir trade listesi."""
    repo = TradeRepository(db)
    trades, total = await repo.get_filtered(
        status=status_filter, symbol=symbol, limit=limit, offset=offset,
        sort_by=sort_by, sort_order=sort_order,
    )
    return PaginatedResponse(
        items=[TradeRead.model_validate(t) for t in trades],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/open", response_model=list[TradeRead])
async def list_open_trades(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> list[TradeRead]:
    """Açık pozisyonlar."""
    repo = TradeRepository(db)
    trades = await repo.get_open_trades()
    return [TradeRead.model_validate(t) for t in trades]


@router.get("/stats", response_model=TradeStatsResponse)
async def trade_stats(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> TradeStatsResponse:
    """Trade istatistikleri."""
    repo = TradeRepository(db)
    stats = await repo.get_stats()
    return TradeStatsResponse(**stats)


@router.get("/{trade_id}", response_model=TradeRead)
async def get_trade(
    trade_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> TradeRead:
    """Tekil trade detayı."""
    repo = TradeRepository(db)
    trade = await repo.get_by_id(trade_id)
    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade bulunamadı")
    return TradeRead.model_validate(trade)
