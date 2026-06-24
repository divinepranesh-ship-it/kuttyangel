"""
Night Mode — restricts the group during configured hours.
/nightmode on|off
/nightmode set <HH:MM> <HH:MM>   (start end)
/nightmode status
"""
import logging
from datetime import datetime
import pytz
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler, Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import get_settings, update_setting
from utils import is_admin, send_log, MUTE_PERMISSIONS, FULL_PERMISSIONS

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def set_scheduler(s: AsyncIOScheduler):
    global _scheduler
    _scheduler = s


async def _lock_group(bot, chat_id: int):
    try:
        await bot.set_chat_permissions(chat_id, MUTE_PERMISSIONS)
        await bot.send_message(chat_id,
            "🌙 <b>Night Mode ON</b> — The group is now locked. Good night! 😴",
            parse_mode="HTML")
        await send_log(bot, chat_id, f"🌙 NIGHT MODE ON | Chat ID: {chat_id}")
    except Exception as e:
        logger.error("Night lock failed for %s: %s", chat_id, e)


async def _unlock_group(bot, chat_id: int):
    try:
        await bot.set_chat_permissions(chat_id, FULL_PERMISSIONS)
        await bot.send_message(chat_id,
            "☀️ <b>Night Mode OFF</b> — Good morning! The group is open again.",
            parse_mode="HTML")
        await send_log(bot, chat_id, f"☀️ NIGHT MODE OFF | Chat ID: {chat_id}")
    except Exception as e:
        logger.error("Night unlock failed for %s: %s", chat_id, e)


def _schedule_night_jobs(bot, chat_id: int, night_start: str, night_end: str):
    if _scheduler is None:
        return
    sh, sm = map(int, night_start.split(":"))
    eh, em = map(int, night_end.split(":"))

    lock_id = f"night_lock_{chat_id}"
    unlock_id = f"night_unlock_{chat_id}"

    # Remove existing jobs
    for jid in (lock_id, unlock_id):
        if _scheduler.get_job(jid):
            _scheduler.remove_job(jid)

    _scheduler.add_job(
        _lock_group, CronTrigger(hour=sh, minute=sm),
        args=[bot, chat_id], id=lock_id, replace_existing=True
    )
    _scheduler.add_job(
        _unlock_group, CronTrigger(hour=eh, minute=em),
        args=[bot, chat_id], id=unlock_id, replace_existing=True
    )
    logger.info("Scheduled night mode for chat %s: lock=%s unlock=%s", chat_id, night_start, night_end)


async def nightmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    args = context.args
    settings = await get_settings(chat.id)

    if not args or args[0] == "status":
        enabled = settings.get("night_mode", 0)
        start = settings.get("night_start", "22:00")
        end = settings.get("night_end", "06:00")
        status = "🟢 ON" if enabled else "🔴 OFF"
        return await update.message.reply_text(
            f"🌙 <b>Night Mode</b>: {status}\n"
            f"🕙 Lock time: <b>{start}</b>\n"
            f"☀️ Unlock time: <b>{end}</b>",
            parse_mode="HTML"
        )

    if args[0] == "on":
        await update_setting(chat.id, "night_mode", 1)
        start = settings.get("night_start", "22:00")
        end = settings.get("night_end", "06:00")
        _schedule_night_jobs(context.bot, chat.id, start, end)
        await update.message.reply_text(
            f"🌙 Night Mode <b>enabled</b>.\n"
            f"Lock: {start} | Unlock: {end}",
            parse_mode="HTML"
        )

    elif args[0] == "off":
        await update_setting(chat.id, "night_mode", 0)
        for jid in (f"night_lock_{chat.id}", f"night_unlock_{chat.id}"):
            if _scheduler and _scheduler.get_job(jid):
                _scheduler.remove_job(jid)
        await update.message.reply_text("☀️ Night Mode <b>disabled</b>.", parse_mode="HTML")

    elif args[0] == "set" and len(args) == 3:
        start, end = args[1], args[2]
        # Validate HH:MM
        try:
            datetime.strptime(start, "%H:%M")
            datetime.strptime(end, "%H:%M")
        except ValueError:
            return await update.message.reply_text("❌ Use HH:MM format, e.g. /nightmode set 22:00 06:00")

        await update_setting(chat.id, "night_start", start)
        await update_setting(chat.id, "night_end", end)
        if settings.get("night_mode", 0):
            _schedule_night_jobs(context.bot, chat.id, start, end)
        await update.message.reply_text(
            f"✅ Night Mode schedule updated: <b>{start}</b> → <b>{end}</b>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "Usage:\n"
            "/nightmode on|off\n"
            "/nightmode set HH:MM HH:MM\n"
            "/nightmode status"
        )


async def restore_night_schedules(bot, scheduler: AsyncIOScheduler):
    """Re-register night mode jobs on bot restart."""
    from database import aiosqlite, DB_PATH
    import aiosqlite as _aio
    async with _aio.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT chat_id, night_start, night_end FROM chat_settings WHERE night_mode=1"
        )
        rows = await cursor.fetchall()
    for (chat_id, start, end) in rows:
        _schedule_night_jobs(bot, chat_id, start, end)
    logger.info("Restored %d night mode schedules", len(rows))


def register(app):
    app.add_handler(CommandHandler("nightmode", nightmode_cmd))
