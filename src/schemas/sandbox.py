"""Sandbox API şemaları."""

from __future__ import annotations

from pydantic import BaseModel


class SandboxDepositRequest(BaseModel):
    asset: str = "USDT"
    amount: float


class SandboxBalanceItem(BaseModel):
    asset: str
    free: float
    locked: float
    total: float


class SandboxWalletResponse(BaseModel):
    balances: list[SandboxBalanceItem]
    mode: str = "sandbox"


class BinanceAccountResponse(BaseModel):
    balances: list[SandboxBalanceItem]
    can_trade: bool
    account_type: str
