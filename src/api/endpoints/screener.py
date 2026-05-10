"""Screener API endpoint'leri."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_active_user
from src.config import settings
from src.core.events import get_cache
from src.schemas.screener import ScreenerResultsResponse, ScreenerStatus

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("/results", response_model=ScreenerResultsResponse)
async def get_screener_results(
    _user: str = Depends(get_current_active_user),
) -> ScreenerResultsResponse:
    """Son screener tarama sonuçlarını getir."""
    data = await get_cache("screener:latest_results")

    if not data:
        return ScreenerResultsResponse(results=[], total_scanned=0)

    return ScreenerResultsResponse(**data)


@router.get("/status", response_model=ScreenerStatus)
async def get_screener_status(
    _user: str = Depends(get_current_active_user),
) -> ScreenerStatus:
    """Screener durumunu getir."""
    data = await get_cache("screener:status")

    if not data:
        return ScreenerStatus(enabled=settings.screener_enabled)

    return ScreenerStatus(**data)
