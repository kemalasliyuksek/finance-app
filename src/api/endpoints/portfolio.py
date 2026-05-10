"""Portföy endpoint'leri."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user
from src.db.repositories.portfolio_repo import PortfolioRepository
from src.db.session import get_db
from src.schemas.portfolio import PortfolioSnapshotRead

router = APIRouter(tags=["portfolio"])


@router.get("/current", response_model=PortfolioSnapshotRead | None)
async def current_portfolio(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> PortfolioSnapshotRead | None:
    """En son portföy snapshot'ı."""
    repo = PortfolioRepository(db)
    snapshot = await repo.get_latest()
    if not snapshot:
        return None
    return PortfolioSnapshotRead.model_validate(snapshot)


@router.get("/history", response_model=list[PortfolioSnapshotRead])
async def portfolio_history(
    range: str = Query("7d", pattern="^(24h|7d|30d|all)$"),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> list[PortfolioSnapshotRead]:
    """Portföy geçmişi - zaman serisi."""
    repo = PortfolioRepository(db)
    # DB kolonu TIMESTAMP WITHOUT TIME ZONE — naive UTC kullan
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    range_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "all": timedelta(days=365),
    }
    start = now - range_map[range]
    snapshots = await repo.get_range(start, now)
    return [PortfolioSnapshotRead.model_validate(s) for s in snapshots]
