"""Health check endpoint - Prometheus ve Docker healthcheck için."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from src.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Temel sağlık kontrolü."""
    return {
        "status": "healthy",
        "app_mode": settings.app_mode,
        "trading_mode": settings.trading_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/detailed")
async def detailed_health_check() -> dict:
    """Detaylı sağlık kontrolü - DB ve Redis bağlantıları dahil."""
    checks: dict = {
        "app": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Database check
    try:
        from src.db.session import engine

        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Redis check
    try:
        from src.core.events import get_redis

        r = await get_redis()
        await r.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"

    overall = all(
        v == "healthy" for k, v in checks.items() if k not in ("timestamp",)
    )
    checks["status"] = "healthy" if overall else "degraded"
    return checks


# Import burada çünkü yukarıda lazy kullanılıyor
from sqlalchemy import text as sa_text  # noqa: E402
