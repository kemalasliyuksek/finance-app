"""Gerçek Binance hesap bilgileri endpoint'leri (read-only)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_current_active_user
from src.config import settings
from src.core.logging import get_logger
from src.schemas.sandbox import BinanceAccountResponse, SandboxBalanceItem

logger = get_logger("binance_account")

router = APIRouter(prefix="/binance", tags=["binance"])


@router.get("/account", response_model=BinanceAccountResponse)
async def get_binance_account(
    _user: str = Depends(get_current_active_user),
) -> BinanceAccountResponse:
    """Gerçek Binance hesap bilgilerini getir (read-only).

    API key gerektirir. Sandbox modda bile gerçek hesap bilgisi gösterir.
    """
    if not settings.binance_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Binance API key ayarlanmamış",
        )

    from binance import AsyncClient
    from binance.exceptions import BinanceAPIException

    try:
        client = await AsyncClient.create(
            api_key=settings.binance_api_key,
            api_secret=settings.binance_api_secret,
        )
        try:
            account = await client.get_account()
        finally:
            await client.close_connection()

        balances = []
        for b in account.get("balances", []):
            free = Decimal(b["free"])
            locked = Decimal(b["locked"])
            total = free + locked
            if total > 0:
                balances.append(
                    SandboxBalanceItem(
                        asset=b["asset"],
                        free=float(free),
                        locked=float(locked),
                        total=float(total),
                    )
                )

        return BinanceAccountResponse(
            balances=sorted(balances, key=lambda x: x.total, reverse=True),
            can_trade=account.get("canTrade", False),
            account_type=account.get("accountType", "SPOT"),
        )

    except BinanceAPIException as e:
        logger.error("binance_api_error", message=e.message, code=getattr(e, "code", None))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Binance API bağlantı hatası",
        ) from e
