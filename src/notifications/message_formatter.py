"""Telegram mesaj formatlayıcı - sinyaller, raporlar, durum mesajları."""

from __future__ import annotations

from datetime import datetime, timezone


def format_signal_message(data: dict) -> str:
    """Sinyal mesajı formatla - Telegram inline keyboard ile birlikte kullanılır."""
    side = data.get("side", "?")
    symbol = data.get("symbol", "?")
    confidence = data.get("confidence", 0)
    entry = data.get("entry_price", 0)
    sl = data.get("stop_loss")
    tp = data.get("take_profit")
    strategy = data.get("strategy", "?")

    side_emoji = "\U0001f7e2" if side == "BUY" else "\U0001f534"  # green/red circle
    arrow = "\u2b06\ufe0f" if side == "BUY" else "\u2b07\ufe0f"  # up/down arrow

    lines = [
        f"{side_emoji} **{side} {symbol}** {arrow}",
        "",
        f"\U0001f4b0 Giri\u015f: `{_fmt_price(entry)}`",
    ]

    if sl:
        lines.append(f"\U0001f6d1 Stop Loss: `{_fmt_price(sl)}`")
    if tp:
        lines.append(f"\U0001f3af Take Profit: `{_fmt_price(tp)}`")

    # R:R oranı hesapla
    if sl and tp and entry:
        risk = abs(float(entry) - float(sl))
        reward = abs(float(tp) - float(entry))
        rr = reward / risk if risk > 0 else 0
        lines.append(f"\u2696\ufe0f R:R = `1:{rr:.1f}`")

    lines.extend([
        "",
        f"\U0001f4ca G\u00fcven: `{float(confidence) * 100:.1f}%`",
        f"\U0001f9e0 Strateji: `{strategy}`",
        "",
        f"\u23f0 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC",
    ])

    return "\n".join(lines)


def format_trade_executed(data: dict) -> str:
    """Emir yürütüldü mesajı."""
    side = data.get("side", "?")
    symbol = data.get("symbol", "?")
    quantity = data.get("quantity", 0)
    price = data.get("price", 0)
    order_type = data.get("order_type", "?")

    side_emoji = "\U0001f7e2" if side == "BUY" else "\U0001f534"

    return (
        f"{side_emoji} **EM\u0130R Y\u00dcR\u00dcT\u00dcLD\u00dc**\n\n"
        f"\U0001f4c8 {side} {symbol}\n"
        f"\U0001f4b0 Fiyat: `{_fmt_price(price)}`\n"
        f"\U0001f4e6 Miktar: `{quantity}`\n"
        f"\U0001f4cb Tip: `{order_type}`"
    )


def format_trade_closed(data: dict) -> str:
    """Trade kapandı mesajı."""
    symbol = data.get("symbol", "?")
    pnl = data.get("realized_pnl", 0)
    pnl_pct = data.get("realized_pnl_pct", 0)
    duration = data.get("duration_seconds", 0)

    pnl_float = float(pnl)
    emoji = "\U0001f4b5" if pnl_float >= 0 else "\U0001f4b8"  # money/money with wings
    status = "KAR" if pnl_float >= 0 else "ZARAR"
    sign = "+" if pnl_float >= 0 else ""

    duration_str = _fmt_duration(duration)

    return (
        f"{emoji} **TRADE KAPANDI - {status}**\n\n"
        f"\U0001f4c8 {symbol}\n"
        f"\U0001f4b0 PnL: `{sign}{pnl_float:.2f} USDT` ({sign}{float(pnl_pct):.2f}%)\n"
        f"\u23f1\ufe0f S\u00fcre: `{duration_str}`"
    )


def format_portfolio_status(data: dict) -> str:
    """Portföy durumu mesajı."""
    balance = data.get("balance", 0)
    pnl = data.get("total_pnl", 0)
    pnl_pct = data.get("total_pnl_pct", 0)
    open_positions = data.get("open_positions", 0)
    win_rate = data.get("win_rate", 0)
    total_trades = data.get("total_trades", 0)

    pnl_float = float(pnl)
    sign = "+" if pnl_float >= 0 else ""

    return (
        f"\U0001f4bc **PORTF\u00d6Y DURUMU**\n\n"
        f"\U0001f4b0 Bakiye: `{float(balance):.2f} USDT`\n"
        f"\U0001f4c8 PnL: `{sign}{pnl_float:.2f} USDT` ({sign}{float(pnl_pct):.2f}%)\n"
        f"\U0001f4ca A\u00e7\u0131k Pozisyon: `{open_positions}`\n"
        f"\U0001f3af Win Rate: `{float(win_rate):.1f}%`\n"
        f"\U0001f4cb Toplam Trade: `{total_trades}`"
    )


def format_error_message(error: str, context: str = "") -> str:
    """Hata mesajı."""
    msg = f"\u26a0\ufe0f **HATA**\n\n`{error}`"
    if context:
        msg += f"\n\nBa\u011flam: `{context}`"
    return msg


def _fmt_price(price: float | str) -> str:
    """Fiyatı formatla - büyük sayılar için virgül, küçük sayılar için hassasiyet."""
    p = float(price)
    if p >= 1000:
        return f"{p:,.2f}"
    elif p >= 1:
        return f"{p:.4f}"
    else:
        return f"{p:.8f}"


def _fmt_duration(seconds: int) -> str:
    """Süreyi okunabilir formata çevir."""
    if not seconds:
        return "?"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}s {minutes}dk"
    return f"{minutes}dk"
