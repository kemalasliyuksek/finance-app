"""Trading bot Telegram arayüzü - sinyal bildirimleri ve onay sistemi.

Komutlar:
    /start   - Bot başlatma
    /help    - Yardım
    /status  - Bot durumu
    /balance - Bakiye bilgisi
    /signals - Son sinyaller
    /trades  - Son trade'ler
    /pnl     - Kâr/zarar özeti
    /pause   - Botu duraklat
    /resume  - Botu devam ettir
"""

from __future__ import annotations

import asyncio
import json

import redis.asyncio as aioredis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from src.config import settings
from src.constants import RedisChannel
from src.core.events import get_redis
from src.core.logging import get_logger
from src.notifications.approval_handler import (
    CALLBACK_APPROVE,
    CALLBACK_REJECT,
    handle_approval,
    parse_callback_data,
)
from src.notifications.message_formatter import (
    format_error_message,
    format_signal_message,
)

logger = get_logger("telegram_bot")

# Bot durumu
_bot_paused = False


# --- Yetkilendirme Dekoratörü ---


def authorized_only(func):
    """Sadece yetkili chat_id'den gelen komutlara izin ver."""
    import functools

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = str(update.effective_chat.id)
        if chat_id != settings.telegram_chat_id:
            logger.warning(
                "unauthorized_telegram_access",
                chat_id=chat_id,
                user_id=getattr(update.effective_user, "id", None),
                command=update.message.text if update.message else "callback",
            )
            if update.message:
                await update.message.reply_text("\u26d4 Yetkisiz erişim.")
            return
        return await func(update, context)

    return wrapper


# --- Komut Handler'ları ---


@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot başlatma mesajı."""
    await update.message.reply_text(
        "\U0001f916 **Trading Bot Aktif**\n\n"
        f"\U0001f4ca Mod: `{settings.app_mode}`\n"
        f"\u2699\ufe0f Trading: `{settings.trading_mode}`\n"
        f"\U0001f4b1 Çiftler: `{', '.join(settings.trading_pairs)}`\n\n"
        "Komutlar için /help yazın.",
        parse_mode=ParseMode.MARKDOWN,
    )


@authorized_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yardım mesajı."""
    await update.message.reply_text(
        "\U0001f4d6 **Komutlar**\n\n"
        "/status — Bot durumu\n"
        "/balance — Bakiye\n"
        "/signals — Son sinyaller\n"
        "/trades — Son trade'ler\n"
        "/pnl — Kâr/zarar özeti\n"
        "/pause — Duraklat\n"
        "/resume — Devam et\n",
        parse_mode=ParseMode.MARKDOWN,
    )


@authorized_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot durumu."""
    status = "DURAKLATILDI" if _bot_paused else "AKTİF"
    emoji = "\u23f8\ufe0f" if _bot_paused else "\u25b6\ufe0f"

    await update.message.reply_text(
        f"{emoji} **Bot Durumu: {status}**\n\n"
        f"\U0001f4ca Mod: `{settings.app_mode}`\n"
        f"\u2699\ufe0f Trading: `{settings.trading_mode}`\n"
        f"\U0001f4b1 Çiftler: `{', '.join(settings.trading_pairs)}`\n"
        f"\u23f0 İnterval: `{', '.join(settings.candle_intervals)}`\n"
        f"\u26a0\ufe0f Risk/trade: `{settings.risk_per_trade_pct * 100:.1f}%`\n"
        f"\U0001f6d1 Maks pozisyon: `{settings.max_concurrent_positions}`\n"
        f"\U0001f4c9 Günlük limit: `{settings.daily_loss_limit_pct * 100:.1f}%`",
        parse_mode=ParseMode.MARKDOWN,
    )


@authorized_only
async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bakiye bilgisi."""
    try:
        from src.db.repositories.portfolio_repo import PortfolioRepository
        from src.db.session import get_session

        async with get_session() as session:
            repo = PortfolioRepository(session)
            snapshot = await repo.get_latest()

        if not snapshot:
            await update.message.reply_text("\U0001f4b0 Henüz portföy verisi yok.")
            return

        total = float(snapshot.total_balance_usdt)
        free = float(snapshot.free_balance) if snapshot.free_balance else total
        locked = float(snapshot.locked_balance) if snapshot.locked_balance else 0
        open_pos = snapshot.open_positions or 0

        await update.message.reply_text(
            "\U0001f4b0 **Bakiye**\n\n"
            f"\U0001f4b5 Toplam: `{total:.2f} USDT`\n"
            f"\u2705 Kullanılabilir: `{free:.2f} USDT`\n"
            f"\U0001f512 Kilitli: `{locked:.2f} USDT`\n"
            f"\U0001f4ca Açık pozisyon: `{open_pos}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("cmd_balance_error")
        await update.message.reply_text("\u26a0\ufe0f Bakiye bilgisi alınamadı.")


@authorized_only
async def cmd_signals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Son sinyaller."""
    try:
        from src.db.repositories.signal_repo import SignalRepository
        from src.db.session import get_session

        async with get_session() as session:
            repo = SignalRepository(session)
            signals = await repo.get_recent(limit=5)

        if not signals:
            await update.message.reply_text("\U0001f4e1 Henüz sinyal yok.")
            return

        lines = ["\U0001f4e1 **Son 5 Sinyal**\n"]
        for s in signals:
            side_emoji = "\U0001f7e2" if s.side == "BUY" else "\U0001f534"
            conf_pct = float(s.confidence) * 100
            status_map = {
                "pending": "\u23f3",
                "approved": "\u2705",
                "rejected": "\u274c",
                "expired": "\u23f0",
                "executed": "\u2699\ufe0f",
            }
            status_icon = status_map.get(s.status, "\u2753")
            lines.append(
                f"{side_emoji} `{s.symbol}` {s.side} — "
                f"%{conf_pct:.0f} güven {status_icon}"
            )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("cmd_signals_error")
        await update.message.reply_text("\u26a0\ufe0f Sinyal bilgisi alınamadı.")


@authorized_only
async def cmd_trades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Son trade'ler."""
    try:
        from src.db.repositories.trade_repo import TradeRepository
        from src.db.session import get_session

        async with get_session() as session:
            repo = TradeRepository(session)
            open_trades = await repo.get_open_trades()
            closed_trades = await repo.get_closed_trades(limit=5)

        lines = ["\U0001f4c8 **Trade'ler**\n"]

        if open_trades:
            lines.append("_Açık Pozisyonlar:_")
            for t in open_trades:
                entry = float(t.entry_price) if t.entry_price else 0
                lines.append(
                    f"\U0001f7e2 `{t.symbol}` — Giriş: `{entry:.2f}`"
                )
            lines.append("")

        if closed_trades:
            lines.append("_Son Kapanan:_")
            for t in closed_trades:
                pnl = float(t.realized_pnl) if t.realized_pnl else 0
                emoji = "\U0001f4b5" if pnl >= 0 else "\U0001f4b8"
                sign = "+" if pnl >= 0 else ""
                lines.append(
                    f"{emoji} `{t.symbol}` — {sign}{pnl:.2f} USDT"
                )
        elif not open_trades:
            lines.append("Henüz trade yok.")

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("cmd_trades_error")
        await update.message.reply_text("\u26a0\ufe0f Trade bilgisi alınamadı.")


@authorized_only
async def cmd_pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kâr/zarar özeti."""
    try:
        from src.db.repositories.trade_repo import TradeRepository
        from src.db.session import get_session

        async with get_session() as session:
            repo = TradeRepository(session)
            stats = await repo.get_stats()

        if not stats or stats.get("total_trades", 0) == 0:
            await update.message.reply_text("\U0001f4ca Henüz trade istatistiği yok.")
            return

        total = stats.get("total_trades", 0)
        wins = stats.get("winning_trades", 0)
        losses = stats.get("losing_trades", 0)
        win_rate = stats.get("win_rate", 0)
        total_pnl = stats.get("total_pnl", 0)
        avg_win = stats.get("avg_win", 0)
        avg_loss = stats.get("avg_loss", 0)
        best = stats.get("best_trade", 0)
        worst = stats.get("worst_trade", 0)

        pnl_emoji = "\U0001f4b5" if total_pnl >= 0 else "\U0001f4b8"
        sign = "+" if total_pnl >= 0 else ""

        await update.message.reply_text(
            f"{pnl_emoji} **Kâr/Zarar Özeti**\n\n"
            f"\U0001f4cb Toplam trade: `{total}`\n"
            f"\u2705 Kazanan: `{wins}` | \u274c Kaybeden: `{losses}`\n"
            f"\U0001f3af Win rate: `{win_rate:.1f}%`\n\n"
            f"\U0001f4b0 Toplam PnL: `{sign}{total_pnl:.2f} USDT`\n"
            f"\U0001f4c8 Ort. kazanç: `+{avg_win:.2f} USDT`\n"
            f"\U0001f4c9 Ort. kayıp: `{avg_loss:.2f} USDT`\n"
            f"\U0001f31f En iyi: `+{best:.2f} USDT`\n"
            f"\U0001f4a5 En kötü: `{worst:.2f} USDT`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("cmd_pnl_error")
        await update.message.reply_text("\u26a0\ufe0f PnL bilgisi alınamadı.")


@authorized_only
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botu duraklat."""
    global _bot_paused
    _bot_paused = True
    await update.message.reply_text(
        "\u23f8\ufe0f Bot duraklatıldı. Yeni sinyal üretilmeyecek."
    )


@authorized_only
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botu devam ettir."""
    global _bot_paused
    _bot_paused = False
    await update.message.reply_text("\u25b6\ufe0f Bot devam ediyor.")


# --- Callback Handler ---


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline keyboard callback handler - sinyal onay/red."""
    query = update.callback_query

    # Yetkilendirme kontrolü
    chat_id = str(query.message.chat.id)
    if chat_id != settings.telegram_chat_id:
        logger.warning(
            "unauthorized_telegram_callback",
            chat_id=chat_id,
            user_id=getattr(update.effective_user, "id", None),
        )
        await query.answer("Yetkisiz erişim", show_alert=True)
        return

    await query.answer()

    parsed = parse_callback_data(query.data)
    if not parsed:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    action, signal_id = parsed
    approved = action == CALLBACK_APPROVE

    result = await handle_approval(signal_id, approved=approved, user="telegram")

    # Mesajı güncelle
    status_emoji = "\u2705" if result["success"] else "\u274c"
    await query.edit_message_text(
        text=f"{query.message.text}\n\n{status_emoji} {result['message']}",
        parse_mode=ParseMode.MARKDOWN,
    )


# --- Sinyal Bildirim ---


async def send_signal_notification(app: Application, data: dict) -> None:
    """Yeni sinyal için Telegram bildirimi gönder."""
    if _bot_paused:
        logger.info("signal_skipped_bot_paused", signal_id=data.get("signal_id"))
        return

    message = format_signal_message(data)
    signal_id = data.get("signal_id", "")

    reply_markup = None
    if settings.trading_mode == "semi_auto":
        # Yarı otomatik — onay butonları ekle
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "\u2705 Onayla", callback_data=f"{CALLBACK_APPROVE}:{signal_id}"
                    ),
                    InlineKeyboardButton(
                        "\u274c Reddet", callback_data=f"{CALLBACK_REJECT}:{signal_id}"
                    ),
                ]
            ]
        )
    elif settings.trading_mode == "full_auto":
        # Tam otomatik — bilgi notu ekle
        message += "\n\n\u26a1 _Otomatik onaylandı_"

    try:
        await app.bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
        logger.info("signal_notification_sent", signal_id=signal_id)
    except Exception:
        logger.exception("signal_notification_error", signal_id=signal_id)


# --- Redis Listener ---


async def send_risk_rejection_notification(app: Application, data: dict) -> None:
    """Risk kontrolü tarafından reddedilen sinyal bildirimi."""
    symbol = data.get("symbol", "?")
    side = data.get("side", "?")
    reason = data.get("reason", "Bilinmeyen hata")
    side_emoji = "\U0001f7e2" if side == "BUY" else "\U0001f534"

    message = (
        f"\u26a0\ufe0f **Sinyal Reddedildi**\n\n"
        f"{side_emoji} {side} {symbol}\n"
        f"\U0001f6ab Sebep: _{reason}_"
    )

    try:
        await app.bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("risk_rejection_notification_error")


async def redis_signal_listener(app: Application) -> None:
    """Redis'ten sinyal event'lerini dinle ve Telegram'a bildir."""
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(RedisChannel.SIGNAL_NEW, "signal:rejected_by_risk")

    logger.info("telegram_redis_listener_started")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                channel = message.get("channel", b"").decode() if isinstance(message.get("channel"), bytes) else message.get("channel", "")
                data = json.loads(message["data"])
                if channel == "signal:rejected_by_risk":
                    await send_risk_rejection_notification(app, data)
                else:
                    await send_signal_notification(app, data)
            except Exception:
                logger.exception("redis_message_processing_error")
    finally:
        await pubsub.unsubscribe(RedisChannel.SIGNAL_NEW, "signal:rejected_by_risk")
        await pubsub.close()


# --- Ana Bot ---


def create_bot_application() -> Application:
    """Telegram bot uygulaması oluştur."""
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # Komut handler'ları
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("signals", cmd_signals))
    app.add_handler(CommandHandler("trades", cmd_trades))
    app.add_handler(CommandHandler("pnl", cmd_pnl))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))

    # Callback handler (inline keyboard)
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app


async def _load_app_config_on_start() -> None:
    """Telegram container başlangıcında DB'den config'i yükle.

    trading-bot zaten seed'i yapar; telegram buradan sadece okur ve
    kendi yerel settings singleton'ını senkronlar.
    """
    try:
        from src.db.repositories.app_config_repo import AppConfigRepository
        from src.core.config_reload import apply_config_to_settings
        from src.db.session import get_session

        async with get_session() as session:
            repo = AppConfigRepository(session)
            row = await repo.get_current()
            values = repo.to_settings_dict(row)
        await apply_config_to_settings(values)
        logger.info("telegram_app_config_loaded", trading_mode=settings.trading_mode)
    except Exception:
        logger.exception(
            "telegram_app_config_load_failed",
            msg="settings singleton in-memory default'larda kalacak",
        )


async def run_telegram_bot() -> None:
    """Telegram bot'u ve Redis listener'ı başlat."""
    if not settings.telegram_bot_token:
        logger.warning("telegram_bot_token_not_set")
        return

    # Önce DB'den config'i yükle — sonraki adımlar güncel değerleri görsün
    await _load_app_config_on_start()

    app = create_bot_application()

    async with app:
        await app.start()
        logger.info("telegram_bot_started")

        # Redis listener'ları paralel çalıştır (sinyaller + config reload)
        from src.core.config_reload import config_listener
        listener_task = asyncio.create_task(redis_signal_listener(app))
        config_listener_task = asyncio.create_task(config_listener())

        try:
            await app.updater.start_polling(drop_pending_updates=True)
            # Bot çalışırken bekle
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            listener_task.cancel()
            config_listener_task.cancel()
            await app.updater.stop()
            await app.stop()
            logger.info("telegram_bot_stopped")


if __name__ == "__main__":
    asyncio.run(run_telegram_bot())
