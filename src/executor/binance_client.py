"""Binance API thin wrapper - testnet/live mode destegi."""

from __future__ import annotations

from decimal import Decimal

from binance import AsyncClient
from binance.exceptions import BinanceAPIException

from src.config import settings
from src.core.circuit_breaker import binance_circuit_breaker
from src.core.exceptions import BinanceAPIError
from src.core.logging import get_logger
from src.core.metrics import api_latency_seconds
from src.core.retry import with_retry

logger = get_logger("binance_client")

_client: AsyncClient | None = None


async def get_binance_client() -> AsyncClient:
    """Singleton Binance async client döndür."""
    global _client
    if _client is None:
        if settings.is_testnet:
            _client = await AsyncClient.create(
                api_key=settings.binance_testnet_api_key,
                api_secret=settings.binance_testnet_api_secret,
                testnet=True,
            )
            logger.info("binance_client_created", mode="testnet")
        elif settings.is_sandbox:
            # Sandbox: mainnet client (hesap bilgisi çekmek için key varsa kullan)
            if settings.binance_api_key:
                _client = await AsyncClient.create(
                    api_key=settings.binance_api_key,
                    api_secret=settings.binance_api_secret,
                )
            else:
                _client = await AsyncClient.create()
            logger.info("binance_client_created", mode="sandbox (mainnet)")
        else:
            _client = await AsyncClient.create(
                api_key=settings.binance_api_key,
                api_secret=settings.binance_api_secret,
            )
            logger.info("binance_client_created", mode="live")
    return _client


async def close_binance_client() -> None:
    """Binance client baglantisini kapat."""
    global _client
    if _client:
        await _client.close_connection()
        _client = None


async def get_account_balance() -> dict[str, Decimal]:
    """Hesap bakiyelerini getir.

    Sandbox modda sanal cüzdandan, live modda Binance API'den okur.

    Returns:
        {"USDT": Decimal("500.00"), "BTC": Decimal("0.001"), ...}
    """
    if settings.is_sandbox:
        from src.sandbox.wallet import sandbox_wallet
        return await sandbox_wallet.get_account_balance()

    client = await get_binance_client()
    try:
        account = await client.get_account()
        balances = {}
        for b in account.get("balances", []):
            free = Decimal(b["free"])
            locked = Decimal(b["locked"])
            total = free + locked
            if total > 0:
                balances[b["asset"]] = total
        return balances
    except BinanceAPIException as e:
        raise BinanceAPIError(f"Bakiye sorgulama hatası: {e}") from e


@with_retry(max_retries=3, base_delay=0.5, retryable_exceptions=(BinanceAPIError,))
async def get_usdt_balance() -> dict:
    """USDT bakiye detayı (retry korumalı).

    Sandbox modda sanal cüzdandan, live modda Binance API'den okur.

    Returns:
        {"total": Decimal, "free": Decimal, "locked": Decimal}
    """
    if settings.is_sandbox:
        from src.sandbox.wallet import sandbox_wallet
        return await sandbox_wallet.get_usdt_balance()

    async def _get():
        client = await get_binance_client()
        try:
            account = await client.get_account()
        except BinanceAPIException as e:
            raise BinanceAPIError(f"USDT bakiye hatası: {e}") from e

        for b in account.get("balances", []):
            if b["asset"] == "USDT":
                return {
                    "total": Decimal(b["free"]) + Decimal(b["locked"]),
                    "free": Decimal(b["free"]),
                    "locked": Decimal(b["locked"]),
                }
        return {"total": Decimal("0"), "free": Decimal("0"), "locked": Decimal("0")}

    return await binance_circuit_breaker.call(_get)


@with_retry(max_retries=2, base_delay=1.0, retryable_exceptions=(BinanceAPIError,))
async def place_market_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    client_order_id: str | None = None,
) -> dict:
    """Market emir gönder (circuit breaker + retry korumalı).

    Returns:
        Binance order response dict
    """
    async def _place():
        client = await get_binance_client()
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": str(quantity),
        }
        if client_order_id:
            params["newClientOrderId"] = client_order_id

        try:
            order = await client.create_order(**params)
        except BinanceAPIException as e:
            raise BinanceAPIError(f"Market emir hatası: {e}") from e

        logger.info(
            "market_order_placed",
            symbol=symbol,
            side=side,
            quantity=str(quantity),
            order_id=order.get("orderId"),
        )
        return order

    return await binance_circuit_breaker.call(_place)


async def place_limit_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    client_order_id: str | None = None,
) -> dict:
    """Limit emir gonder."""
    client = await get_binance_client()
    try:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": str(quantity),
            "price": str(price),
        }
        if client_order_id:
            params["newClientOrderId"] = client_order_id

        order = await client.create_order(**params)
        logger.info(
            "limit_order_placed",
            symbol=symbol,
            side=side,
            quantity=str(quantity),
            price=str(price),
            order_id=order.get("orderId"),
        )
        return order
    except BinanceAPIException as e:
        raise BinanceAPIError(f"Limit emir hatasi: {e}") from e


async def cancel_order(symbol: str, order_id: int) -> dict:
    """Emri iptal et."""
    client = await get_binance_client()
    try:
        result = await client.cancel_order(symbol=symbol, orderId=order_id)
        logger.info("order_cancelled", symbol=symbol, order_id=order_id)
        return result
    except BinanceAPIException as e:
        raise BinanceAPIError(f"Emir iptal hatasi: {e}") from e


async def get_order_status(symbol: str, order_id: int) -> dict:
    """Emir durumunu sorgula."""
    client = await get_binance_client()
    try:
        return await client.get_order(symbol=symbol, orderId=order_id)
    except BinanceAPIException as e:
        raise BinanceAPIError(f"Emir sorgulama hatasi: {e}") from e


async def get_symbol_info(symbol: str) -> dict | None:
    """Symbol bilgisi (min qty, step size, vb.)."""
    client = await get_binance_client()
    try:
        info = await client.get_exchange_info()
        for s in info.get("symbols", []):
            if s["symbol"] == symbol:
                return s
        return None
    except BinanceAPIException as e:
        raise BinanceAPIError(f"Symbol bilgi hatasi: {e}") from e
