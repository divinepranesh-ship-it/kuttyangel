"""
Settings & logs configuration.
/setlog <channel_id>   — set log channel (bot must be admin there)
/setlog off            — disable logging
/settings              — view all current settings
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError

from database import get_settings, update_setting
from utils import is_admin

logger = logging.getLogger(__name__)


async def setlog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    if not context.args:
        return await update.message.reply_text(
            "Usage:\n/setlog <channel_id>  — enable logging\n/setlog off  — disable"
        )

    if context.args[0].lower() == "off":
        await update_setting(chat.id, "log_channel_id", None)
        return await update.message.reply_text("✅ Logging disabled.")

    try:
        channel_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Provide a numeric channel/chat ID.")

    # Verify bot can send there
    try:
        await context.bot.send_message(channel_id,
            f"✅ Log channel set for <b>{chat.title}</b>.", parse_mode="HTML")
        await update_setting(chat.id, "log_channel_id", channel_id)
        await update.message.reply_text(f"✅ Log channel set to <code>{channel_id}</code>.", parse_mode="HTML")
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ Could not send to that channel: {e}\n"
            "Make sure the bot is an admin in the log channel."
        )


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    s = await get_settings(chat.id)
    night_status = "🟢 ON" if s.get("night_mode") else "🔴 OFF"
    welcome_status = "🟢 ON" if s.get("welcome_enabled", 1) else "🔴 OFF"
    log_ch = s.get("log_channel_id") or "Not set"

    text = (
        f"⚙️ <b>Settings for {chat.title}</b>\n\n"
        f"🌙 Night Mode: {night_status}\n"
        f"   Lock: {s.get('night_start', '22:00')} | Unlock: {s.get('night_end', '06:00')}\n\n"
        f"👋 Welcome Message: {welcome_status}\n\n"
        f"⚠️ Max Warnings: {s.get('max_warns', 3)}\n\n"
        f"📋 Log Channel: <code>{log_ch}</code>\n\n"
        f"<i>Use /help to see all commands.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


def register(app):
    app.add_handler(CommandHandler("setlog", setlog_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
