"""
Welcome message handler.
/setwelcome <message>  — set welcome text (supports {name}, {username}, {chat})
/welcome on|off        — toggle welcome
/welcome               — show current welcome message
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from database import get_settings, update_setting
from utils import is_admin

logger = logging.getLogger(__name__)


def _format_welcome(template: str, user, chat) -> str:
    username = f"@{user.username}" if user.username else user.full_name
    return (template
            .replace("{name}", user.full_name)
            .replace("{username}", username)
            .replace("{chat}", chat.title or "this group"))


async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    settings = await get_settings(chat.id)

    if not settings.get("welcome_enabled", 1):
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        template = settings.get("welcome_msg") or (
            "👋 Welcome, <b>{name}</b>! Glad to have you in <b>{chat}</b>.\n"
            "Please read the rules and enjoy your stay!"
        )
        text = _format_welcome(template, member, chat)
        await chat.send_message(text, parse_mode="HTML")


async def setwelcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    if not context.args:
        return await update.message.reply_text(
            "Usage: /setwelcome <message>\n"
            "Variables: {name} {username} {chat}"
        )

    msg = " ".join(context.args)
    await update_setting(chat.id, "welcome_msg", msg)
    await update.message.reply_text("✅ Welcome message saved.", parse_mode="HTML")


async def welcome_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    settings = await get_settings(chat.id)

    if not context.args:
        msg = settings.get("welcome_msg", "Default welcome message")
        status = "🟢 ON" if settings.get("welcome_enabled", 1) else "🔴 OFF"
        return await update.message.reply_text(
            f"Welcome status: {status}\n\nMessage:\n{msg}", parse_mode="HTML"
        )

    if context.args[0] == "on":
        await update_setting(chat.id, "welcome_enabled", 1)
        await update.message.reply_text("✅ Welcome message <b>enabled</b>.", parse_mode="HTML")
    elif context.args[0] == "off":
        await update_setting(chat.id, "welcome_enabled", 0)
        await update.message.reply_text("✅ Welcome message <b>disabled</b>.", parse_mode="HTML")
    else:
        await update.message.reply_text("Usage: /welcome on|off")


def register(app):
    app.add_handler(CommandHandler("setwelcome", setwelcome_cmd))
    app.add_handler(CommandHandler("welcome", welcome_toggle_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))
