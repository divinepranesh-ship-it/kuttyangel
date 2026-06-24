"""
Moderation commands: /ban /unban /mute /unmute /warn /unwarn /warnings /kick
All commands require the caller to be an admin.
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError

from database import (
    add_warning, get_warning_count, get_warnings,
    reset_warnings, get_settings, update_setting
)
from utils import is_admin, send_log, mention_html, MUTE_PERMISSIONS, FULL_PERMISSIONS

logger = logging.getLogger(__name__)


def _parse_time(arg: str):
    """Parse e.g. '10m' '2h' '1d' → timedelta or None."""
    if not arg:
        return None
    unit = arg[-1].lower()
    try:
        value = int(arg[:-1])
    except ValueError:
        return None
    return {"m": timedelta(minutes=value), "h": timedelta(hours=value), "d": timedelta(days=value)}.get(unit)


async def _get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return (user, reason) extracted from reply or args."""
    msg = update.effective_message
    reason = ""
    if msg.reply_to_message:
        user = msg.reply_to_message.from_user
        reason = " ".join(context.args) if context.args else ""
    elif context.args:
        try:
            user = await context.bot.get_chat(context.args[0])
            reason = " ".join(context.args[1:])
        except TelegramError:
            await msg.reply_text("❌ User not found.")
            return None, None
    else:
        await msg.reply_text("❌ Reply to a user or provide their @username / ID.")
        return None, None
    return user, reason


# ─── /ban ─────────────────────────────────────────────────────────────────────

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    user, reason = await _get_target(update, context)
    if not user:
        return

    try:
        await chat.ban_member(user.id)
        text = (f"🔨 {mention_html(user.id, user.full_name)} has been <b>banned</b>.\n"
                f"Reason: {reason or 'No reason given'}")
        await update.message.reply_text(text, parse_mode="HTML")
        await send_log(context.bot, chat.id,
                       f"🔨 BAN | Chat: {chat.title}\n"
                       f"User: {mention_html(user.id, user.full_name)} ({user.id})\n"
                       f"By: {mention_html(caller.id, caller.full_name)}\n"
                       f"Reason: {reason or '-'}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed: {e}")


# ─── /unban ───────────────────────────────────────────────────────────────────

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    user, _ = await _get_target(update, context)
    if not user:
        return

    try:
        await chat.unban_member(user.id)
        await update.message.reply_text(
            f"✅ {mention_html(user.id, user.full_name)} has been <b>unbanned</b>.",
            parse_mode="HTML"
        )
        await send_log(context.bot, chat.id,
                       f"✅ UNBAN | Chat: {chat.title}\n"
                       f"User: {mention_html(user.id, user.full_name)}\n"
                       f"By: {mention_html(caller.id, caller.full_name)}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed: {e}")


# ─── /kick ────────────────────────────────────────────────────────────────────

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    user, reason = await _get_target(update, context)
    if not user:
        return

    try:
        await chat.ban_member(user.id)
        await chat.unban_member(user.id)  # unban right away = kick
        text = (f"👢 {mention_html(user.id, user.full_name)} has been <b>kicked</b>.\n"
                f"Reason: {reason or 'No reason given'}")
        await update.message.reply_text(text, parse_mode="HTML")
        await send_log(context.bot, chat.id,
                       f"👢 KICK | Chat: {chat.title}\n"
                       f"User: {mention_html(user.id, user.full_name)}\n"
                       f"By: {mention_html(caller.id, caller.full_name)}\n"
                       f"Reason: {reason or '-'}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed: {e}")


# ─── /mute ────────────────────────────────────────────────────────────────────

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    user, reason = await _get_target(update, context)
    if not user:
        return

    # Optional duration: /mute @user 1h reason
    until_date = None
    duration_str = ""
    if context.args:
        td = _parse_time(context.args[0] if not context.args[0].startswith("@") else
                         (context.args[1] if len(context.args) > 1 else ""))
        if td:
            until_date = datetime.utcnow() + td
            duration_str = f" for {context.args[0]}"

    try:
        await chat.restrict_member(user.id, MUTE_PERMISSIONS, until_date=until_date)
        text = (f"🔇 {mention_html(user.id, user.full_name)} has been <b>muted</b>{duration_str}.\n"
                f"Reason: {reason or 'No reason given'}")
        await update.message.reply_text(text, parse_mode="HTML")
        await send_log(context.bot, chat.id,
                       f"🔇 MUTE | Chat: {chat.title}\n"
                       f"User: {mention_html(user.id, user.full_name)}\n"
                       f"Duration: {duration_str or 'indefinite'}\n"
                       f"By: {mention_html(caller.id, caller.full_name)}\n"
                       f"Reason: {reason or '-'}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed: {e}")


# ─── /unmute ──────────────────────────────────────────────────────────────────

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    user, _ = await _get_target(update, context)
    if not user:
        return

    try:
        await chat.restrict_member(user.id, FULL_PERMISSIONS)
        await update.message.reply_text(
            f"🔊 {mention_html(user.id, user.full_name)} has been <b>unmuted</b>.",
            parse_mode="HTML"
        )
        await send_log(context.bot, chat.id,
                       f"🔊 UNMUTE | Chat: {chat.title}\n"
                       f"User: {mention_html(user.id, user.full_name)}\n"
                       f"By: {mention_html(caller.id, caller.full_name)}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed: {e}")


# ─── /warn ────────────────────────────────────────────────────────────────────

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    user, reason = await _get_target(update, context)
    if not user:
        return

    settings = await get_settings(chat.id)
    max_warns = settings.get("max_warns", 3)

    count = await add_warning(chat.id, user.id, reason)
    if count >= max_warns:
        try:
            await chat.ban_member(user.id)
            text = (f"⛔ {mention_html(user.id, user.full_name)} reached {count}/{max_warns} warnings "
                    f"and has been <b>banned</b>.")
            await reset_warnings(chat.id, user.id)
        except TelegramError:
            text = f"⚠️ {mention_html(user.id, user.full_name)} has {count}/{max_warns} warnings (ban failed)."
    else:
        text = (f"⚠️ {mention_html(user.id, user.full_name)} warned ({count}/{max_warns}).\n"
                f"Reason: {reason or 'No reason given'}")

    await update.message.reply_text(text, parse_mode="HTML")
    await send_log(context.bot, chat.id,
                   f"⚠️ WARN | Chat: {chat.title}\n"
                   f"User: {mention_html(user.id, user.full_name)}\n"
                   f"Count: {count}/{max_warns}\n"
                   f"By: {mention_html(caller.id, caller.full_name)}\n"
                   f"Reason: {reason or '-'}")


# ─── /unwarn ──────────────────────────────────────────────────────────────────

async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    user, _ = await _get_target(update, context)
    if not user:
        return

    await reset_warnings(chat.id, user.id)
    await update.message.reply_text(
        f"✅ Warnings cleared for {mention_html(user.id, user.full_name)}.",
        parse_mode="HTML"
    )


# ─── /warnings ───────────────────────────────────────────────────────────────

async def warnings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user, _ = await _get_target(update, context)
    if not user:
        return

    settings = await get_settings(chat.id)
    max_warns = settings.get("max_warns", 3)
    warns = await get_warnings(chat.id, user.id)
    if not warns:
        return await update.message.reply_text(
            f"✅ {mention_html(user.id, user.full_name)} has no warnings.",
            parse_mode="HTML"
        )

    lines = [f"⚠️ Warnings for {mention_html(user.id, user.full_name)} ({len(warns)}/{max_warns}):"]
    for i, (reason, ts) in enumerate(warns, 1):
        lines.append(f"  {i}. {reason or 'No reason'} — <i>{ts}</i>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ─── /setwarn ────────────────────────────────────────────────────────────────

async def setwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("Usage: /setwarn <number>")

    limit = int(context.args[0])
    await update_setting(chat.id, "max_warns", limit)
    await update.message.reply_text(f"✅ Max warnings set to <b>{limit}</b>.", parse_mode="HTML")


# ─── Handler registration ─────────────────────────────────────────────────────

def register(app):
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("unwarn", unwarn_cmd))
    app.add_handler(CommandHandler("warnings", warnings_cmd))
    app.add_handler(CommandHandler("setwarn", setwarn_cmd))
