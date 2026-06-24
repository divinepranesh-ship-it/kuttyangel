"""
Blocklist (banned words) handler.
/addblock <word>  — add word to blocklist
/rmblock <word>   — remove word
/blocklist        — show all blocked words
Any message containing a blocked word is deleted; sender gets warned.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError

from database import add_blocked_word, remove_blocked_word, get_blocked_words, add_warning, get_settings
from utils import is_admin, send_log, mention_html, MUTE_PERMISSIONS

logger = logging.getLogger(__name__)


async def addblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /addblock <word>")

    word = " ".join(context.args).lower()
    added = await add_blocked_word(chat.id, word)
    if added:
        await update.message.reply_text(f"✅ <b>{word}</b> added to blocklist.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"ℹ️ <b>{word}</b> is already blocked.", parse_mode="HTML")


async def rmblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /rmblock <word>")

    word = " ".join(context.args).lower()
    removed = await remove_blocked_word(chat.id, word)
    if removed:
        await update.message.reply_text(f"✅ <b>{word}</b> removed from blocklist.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"ℹ️ <b>{word}</b> was not in the blocklist.", parse_mode="HTML")


async def show_blocklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    words = await get_blocked_words(chat.id)
    if not words:
        return await update.message.reply_text("📋 Blocklist is empty.")
    await update.message.reply_text(
        "🚫 <b>Blocked words:</b>\n" + "\n".join(f"• <code>{w}</code>" for w in words),
        parse_mode="HTML"
    )


async def check_blocklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not msg or not msg.text:
        return
    if await is_admin(chat, user.id):
        return

    words = await get_blocked_words(chat.id)
    text_lower = msg.text.lower()
    triggered = [w for w in words if w in text_lower]
    if not triggered:
        return

    try:
        await msg.delete()
    except TelegramError:
        pass

    settings = await get_settings(chat.id)
    max_warns = settings.get("max_warns", 3)
    count = await add_warning(chat.id, user.id, f"Blocked word: {triggered[0]}")

    if count >= max_warns:
        try:
            await chat.ban_member(user.id)
            notice = (f"⛔ {mention_html(user.id, user.full_name)} used a blocked word and "
                      f"reached {count}/{max_warns} warnings — <b>banned</b>.")
        except TelegramError:
            notice = (f"⚠️ {mention_html(user.id, user.full_name)} used a blocked word "
                      f"({count}/{max_warns} warnings).")
    else:
        notice = (f"⚠️ {mention_html(user.id, user.full_name)}'s message was deleted for containing "
                  f"a blocked word. Warning {count}/{max_warns}.")

    sent = await chat.send_message(notice, parse_mode="HTML")
    await send_log(context.bot, chat.id,
                   f"🚫 BLOCKLIST | Chat: {chat.title}\n"
                   f"User: {mention_html(user.id, user.full_name)}\n"
                   f"Word: {triggered[0]}\nWarning: {count}/{max_warns}")
    # Auto-delete notice after 15 s
    context.job_queue.run_once(
        lambda _: sent.delete(),
        when=15,
        name=f"del_notice_{sent.message_id}"
    )


def register(app):
    app.add_handler(CommandHandler("addblock", addblock_cmd))
    app.add_handler(CommandHandler("rmblock", rmblock_cmd))
    app.add_handler(CommandHandler("blocklist", show_blocklist_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_blocklist))
