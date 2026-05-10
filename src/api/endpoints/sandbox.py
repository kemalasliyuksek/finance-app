"""Sandbox cüzdan ve yönetim endpoint'leri."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.dependencies import get_current_active_user
from src.api.middleware.rate_limit import limiter
from src.config import settings
from src.sandbox.wallet import sandbox_wallet
from src.schemas.sandbox import (
    SandboxBalanceItem,
    SandboxDepositRequest,
    SandboxWalletResponse,
)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


def _require_sandbox():
    """Sandbox modda değilse hata ver."""
    if not settings.is_sandbox:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu işlem sadece sandbox modunda kullanılabilir",
        )


@router.get("/wallet", response_model=SandboxWalletResponse)
async def get_wallet(
    _user: str = Depends(get_current_active_user),
) -> SandboxWalletResponse:
    """Sandbox cüzdan bakiyelerini getir."""
    _require_sandbox()

    all_bal = await sandbox_wallet.get_all_balances()
    items = [
        SandboxBalanceItem(
            asset=asset,
            free=float(info["free"]),
            locked=float(info["locked"]),
            total=float(info["total"]),
        )
        for asset, info in sorted(all_bal.items())
    ]

    return SandboxWalletResponse(balances=items)


@router.post("/deposit", response_model=SandboxWalletResponse)
@limiter.limit("5/minute")
async def deposit(
    request: Request,
    body: SandboxDepositRequest,
    _user: str = Depends(get_current_active_user),
) -> SandboxWalletResponse:
    """Sandbox cüzdana bakiye yükle."""
    _require_sandbox()

    if body.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Miktar pozitif olmalı",
        )

    await sandbox_wallet.deposit(body.asset.upper(), Decimal(str(body.amount)))

    # Güncel cüzdanı dön
    return await get_wallet(_user=_user)


@router.post("/withdraw", response_model=SandboxWalletResponse)
async def withdraw(
    body: SandboxDepositRequest,
    _user: str = Depends(get_current_active_user),
) -> SandboxWalletResponse:
    """Sandbox cüzdandan bakiye çek."""
    _require_sandbox()

    try:
        await sandbox_wallet.withdraw(body.asset.upper(), Decimal(str(body.amount)))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    return await get_wallet(_user=_user)


@router.post("/reset")
@limiter.limit("3/minute")
async def reset_sandbox(
    request: Request,
    _user: str = Depends(get_current_active_user),
) -> dict:
    """Tüm sandbox verisini sıfırla (cüzdan + trade + order + sinyal)."""
    _require_sandbox()

    from sqlalchemy import text
    from src.db.session import get_session

    # Cüzdanı sıfırla
    await sandbox_wallet.reset()

    # DB tablolarını temizle
    async with get_session() as session:
        await session.execute(text("DELETE FROM trading.trades"))
        await session.execute(text("DELETE FROM trading.orders"))
        await session.execute(text("DELETE FROM trading.signals"))
        await session.execute(text("DELETE FROM trading.portfolio_snapshots"))

    return {"status": "ok", "message": "Sandbox sıfırlandı"}
