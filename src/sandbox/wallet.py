"""Sandbox sanal cüzdan — Redis-backed bakiye yönetimi.

Gerçek Binance hesabına dokunmadan sanal bakiye ile trade simülasyonu yapar.
Tüm bakiyeler Redis'te saklanır, container restart'ta korunur (Redis persistence).
Atomik Lua script ile race condition önlenir.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from src.core.events import get_redis
from src.core.logging import get_logger

logger = get_logger("sandbox.wallet")

_KEY_PREFIX = "sandbox:wallet"

# Atomik withdraw Lua script — bakiye kontrolü + çekme tek seferde
_LUA_WITHDRAW = """
local data = redis.call('GET', KEYS[1])
if not data then return cjson.encode({err='no_balance'}) end
local bal = cjson.decode(data)
local free = tonumber(bal.free) or 0
local amount = tonumber(ARGV[1])
if free < amount then return cjson.encode({err='insufficient', free=tostring(free)}) end
bal.free = tostring(free - amount)
redis.call('SET', KEYS[1], cjson.encode(bal))
return cjson.encode(bal)
"""

# Atomik deposit Lua script — bakiye ekleme tek seferde
_LUA_DEPOSIT = """
local data = redis.call('GET', KEYS[1])
local bal
if data then
    bal = cjson.decode(data)
else
    bal = {free='0', locked='0'}
end
bal.free = tostring((tonumber(bal.free) or 0) + tonumber(ARGV[1]))
redis.call('SET', KEYS[1], cjson.encode(bal))
return cjson.encode(bal)
"""


class SandboxWallet:
    """Redis-backed sanal cüzdan — atomik operasyonlar."""

    async def deposit(self, asset: str, amount: Decimal) -> dict:
        """Cüzdana bakiye yükle (atomik)."""
        if amount <= 0:
            raise ValueError("Yükleme miktarı pozitif olmalı")

        asset = asset.upper()
        r = await get_redis()
        result = await r.eval(_LUA_DEPOSIT, 1, f"{_KEY_PREFIX}:{asset}", str(amount))
        bal = self._parse_lua_result(result)

        logger.info("sandbox_deposit", asset=asset, amount=float(amount), new_free=float(bal["free"]))
        return self._format(bal)

    async def withdraw(self, asset: str, amount: Decimal) -> dict:
        """Cüzdandan bakiye çek (atomik — race condition korumalı)."""
        if amount <= 0:
            raise ValueError("Çekme miktarı pozitif olmalı")

        asset = asset.upper()
        r = await get_redis()
        result = await r.eval(_LUA_WITHDRAW, 1, f"{_KEY_PREFIX}:{asset}", str(amount))
        parsed = json.loads(result)

        if "err" in parsed:
            if parsed["err"] == "insufficient":
                raise ValueError(
                    f"Yetersiz bakiye: {parsed.get('free', '0')} {asset} mevcut, {amount} istendi"
                )
            raise ValueError(f"Bakiye hatası: {parsed['err']}")

        bal = {
            "free": Decimal(str(parsed.get("free", "0"))),
            "locked": Decimal(str(parsed.get("locked", "0"))),
        }

        logger.info("sandbox_withdraw", asset=asset, amount=float(amount), new_free=float(bal["free"]))
        return self._format(bal)

    async def get_balance(self, asset: str) -> dict:
        """Tek asset bakiyesi."""
        bal = await self._get_raw(asset.upper())
        return self._format(bal)

    async def get_all_balances(self) -> dict[str, dict]:
        """Tüm asset bakiyeleri (sıfır olmayanlar)."""
        r = await get_redis()
        keys = []
        async for key in r.scan_iter(match=f"{_KEY_PREFIX}:*"):
            keys.append(key)

        result = {}
        for key in keys:
            asset = key.split(":")[-1]
            bal = await self._get_raw(asset)
            total = bal["free"] + bal["locked"]
            if total > 0:
                result[asset] = self._format(bal)

        return result

    async def get_usdt_balance(self) -> dict:
        """USDT bakiyesi — binance_client.get_usdt_balance() uyumlu format."""
        bal = await self._get_raw("USDT")
        return {
            "total": bal["free"] + bal["locked"],
            "free": bal["free"],
            "locked": bal["locked"],
        }

    async def get_account_balance(self) -> dict[str, Decimal]:
        """Tüm bakiyeler — binance_client.get_account_balance() uyumlu format."""
        all_bal = await self.get_all_balances()
        return {asset: info["total"] for asset, info in all_bal.items()}

    async def reset(self) -> None:
        """Tüm sandbox bakiyelerini sıfırla."""
        r = await get_redis()
        keys = []
        async for key in r.scan_iter(match=f"{_KEY_PREFIX}:*"):
            keys.append(key)
        if keys:
            await r.delete(*keys)
        logger.info("sandbox_wallet_reset")

    # --- Internal ---

    async def _get_raw(self, asset: str) -> dict:
        """Redis'ten ham bakiye oku."""
        r = await get_redis()
        data = await r.get(f"{_KEY_PREFIX}:{asset}")
        if data is None:
            return {"free": Decimal("0"), "locked": Decimal("0")}
        try:
            parsed = json.loads(data)
            return {
                "free": Decimal(str(parsed.get("free", "0"))),
                "locked": Decimal(str(parsed.get("locked", "0"))),
            }
        except (json.JSONDecodeError, InvalidOperation):
            return {"free": Decimal("0"), "locked": Decimal("0")}

    @staticmethod
    def _parse_lua_result(result) -> dict:
        """Lua script sonucunu parse et."""
        parsed = json.loads(result)
        return {
            "free": Decimal(str(parsed.get("free", "0"))),
            "locked": Decimal(str(parsed.get("locked", "0"))),
        }

    @staticmethod
    def _format(bal: dict) -> dict:
        """Standart bakiye formatı."""
        return {
            "free": bal["free"],
            "locked": bal["locked"],
            "total": bal["free"] + bal["locked"],
        }


# Singleton instance
sandbox_wallet = SandboxWallet()
