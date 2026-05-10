"""Ana API router - tüm endpoint'leri birleştirir."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.endpoints import (
    auth,
    binance_account,
    candles,
    config_api,
    dashboard,
    health,
    market,
    orders,
    portfolio,
    sandbox,
    screener,
    sentiment,
    signals,
    trades,
    ws,
)

# /api/v1 prefix'li router - dashboard API'si
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router, prefix="/auth")
api_v1_router.include_router(dashboard.router, prefix="/dashboard")
api_v1_router.include_router(signals.router, prefix="/signals")
api_v1_router.include_router(orders.router, prefix="/orders")
api_v1_router.include_router(trades.router, prefix="/trades")
api_v1_router.include_router(portfolio.router, prefix="/portfolio")
api_v1_router.include_router(candles.router, prefix="/candles")
api_v1_router.include_router(config_api.router, prefix="/config")
api_v1_router.include_router(sentiment.router, prefix="/sentiment")
api_v1_router.include_router(screener.router)
api_v1_router.include_router(sandbox.router)
api_v1_router.include_router(binance_account.router)
api_v1_router.include_router(market.router)

# Ana router - health check'ler root'ta kalır
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(api_v1_router)
api_router.include_router(ws.router)
