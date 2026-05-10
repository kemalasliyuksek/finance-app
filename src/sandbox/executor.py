"""Sandbox emir simülasyonu — Binance'e hiçbir şey göndermez.

Mevcut piyasa fiyatından anında fill simüle eder.
Dönüş formatı Binance API response ile uyumludur (order_manager değişmeden çalışır).
Hata durumunda wallet değişiklikleri geri alınır.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from src.constants import BINANCE_FEE_RATE, Side
from src.core.logging import get_logger
from src.sandbox.wallet import sandbox_wallet

logger = get_logger("sandbox.executor")


async def sandbox_place_market_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    entry_price: Decimal,
    client_order_id: str | None = None,
) -> dict:
    """Market emir simülasyonu.

    Hata durumunda wallet değişiklikleri geri alınır (rollback).
    """
    fill_price = entry_price
    fee_rate = Decimal(str(BINANCE_FEE_RATE))
    cost = quantity * fill_price
    commission = cost * fee_rate

    # Base asset (ör: BTCUSDT → BTC)
    base_asset = symbol.replace("USDT", "")

    if side == Side.BUY:
        total_cost = cost + commission
        usdt_bal = await sandbox_wallet.get_balance("USDT")
        if usdt_bal["free"] < total_cost:
            raise ValueError(
                f"Yetersiz USDT bakiye: {usdt_bal['free']} mevcut, "
                f"{total_cost} gerekli ({cost} + {commission} komisyon)"
            )
        # Withdraw + Deposit — hata olursa rollback
        await sandbox_wallet.withdraw("USDT", total_cost)
        try:
            await sandbox_wallet.deposit(base_asset, quantity)
        except Exception:
            # Deposit başarısız → USDT'yi geri yükle
            await sandbox_wallet.deposit("USDT", total_cost)
            raise

    elif side == Side.SELL:
        coin_bal = await sandbox_wallet.get_balance(base_asset)
        if coin_bal["free"] < quantity:
            raise ValueError(
                f"Yetersiz {base_asset} bakiye: {coin_bal['free']} mevcut, "
                f"{quantity} gerekli"
            )
        await sandbox_wallet.withdraw(base_asset, quantity)
        try:
            net_income = cost - commission
            await sandbox_wallet.deposit("USDT", net_income)
        except Exception:
            # USDT deposit başarısız → coin'i geri yükle
            await sandbox_wallet.deposit(base_asset, quantity)
            raise

    sandbox_order_id = int(uuid.uuid4().int % 10**10)

    logger.info(
        "sandbox_order_filled",
        symbol=symbol,
        side=side,
        quantity=float(quantity),
        price=float(fill_price),
        commission=float(commission),
        sandbox_order_id=sandbox_order_id,
    )

    return {
        "orderId": sandbox_order_id,
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "status": "FILLED",
        "executedQty": str(quantity),
        "cummulativeQuoteQty": str(cost),
        "fills": [
            {
                "price": str(fill_price),
                "qty": str(quantity),
                "commission": str(commission),
                "commissionAsset": "USDT",
            }
        ],
    }
