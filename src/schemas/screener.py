"""Screener API şemaları."""

from __future__ import annotations

from pydantic import BaseModel


class ScreenerResultItem(BaseModel):
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    side: str
    confidence: float
    ta_summary: dict
    scan_score: float
    is_active: bool
    is_volume_top: bool


class ScreenerResultsResponse(BaseModel):
    results: list[ScreenerResultItem]
    total_scanned: int


class ScreenerStatus(BaseModel):
    enabled: bool
    last_scan_at: str | None = None
    cycle_duration_seconds: float | None = None
    total_pairs_scanned: int = 0
    candidates_analyzed: int = 0
    active_pairs: list[str] = []
    volume_top_pairs: list[str] = []
    dynamic_pairs: list[str] = []
