"""Screener filtreleri — USDT çiftlerini hızlıca filtrele.

Saf fonksiyonlar, dış bağımlılık yok.
"""

from __future__ import annotations

from src.config import settings

# Kaldıraçlı token suffix'leri
LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR", "3L", "3S", "5L", "5S")

# Stablecoin USDT çiftleri (USDT bazlı stablecoin ticareti anlamsız)
STABLECOIN_BASES = frozenset({
    "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "GUSD",
    "FRAX", "LUSD", "SUSD", "USDD", "PYUSD", "EURC", "EUR",
    "USD1", "AEUR", "BFUSD",
})


def is_usdt_pair(symbol: str) -> bool:
    """USDT ile biten geçerli bir çift mi? Sadece ASCII harfler ve rakamlar."""
    return symbol.endswith("USDT") and len(symbol) > 4 and symbol.isascii() and symbol.isalnum()


def is_leveraged_token(symbol: str) -> bool:
    """Kaldıraçlı token mu? (BTCUP, ETHDOWN, SOL3L, vb.)"""
    base = symbol.replace("USDT", "")
    return any(base.endswith(suffix) for suffix in LEVERAGED_SUFFIXES)


def is_stablecoin_pair(symbol: str) -> bool:
    """USDT bazlı stablecoin çifti mi?"""
    base = symbol.replace("USDT", "")
    return base in STABLECOIN_BASES


def is_blacklisted(symbol: str) -> bool:
    """Kullanıcı kara listesinde mi?"""
    return symbol in settings.screener_blacklist


def passes_min_volume(ticker: dict, min_volume: float) -> bool:
    """24s USDT hacmi minimum eşiği geçiyor mu?"""
    try:
        quote_volume = float(ticker.get("quoteVolume", 0))
        return quote_volume >= min_volume
    except (ValueError, TypeError):
        return False


def passes_momentum(ticker: dict, min_change_pct: float) -> bool:
    """24s fiyat değişimi minimum eşiği geçiyor mu?"""
    try:
        change = abs(float(ticker.get("priceChangePercent", 0)))
        return change >= min_change_pct
    except (ValueError, TypeError):
        return False


def filter_tickers(tickers: list[dict]) -> list[dict]:
    """Tüm filtreleri uygula, geçerli USDT çiftlerini döndür."""
    min_volume = settings.screener_min_volume_usdt
    min_change = settings.screener_min_change_pct

    filtered = []
    for ticker in tickers:
        symbol = ticker.get("symbol", "")

        if not is_usdt_pair(symbol):
            continue
        if is_leveraged_token(symbol):
            continue
        if is_stablecoin_pair(symbol):
            continue
        if is_blacklisted(symbol):
            continue
        if not passes_min_volume(ticker, min_volume):
            continue
        if not passes_momentum(ticker, min_change):
            continue

        filtered.append(ticker)

    return filtered
