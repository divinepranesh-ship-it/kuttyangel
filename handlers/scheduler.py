"""
Scheduled messages.
/schedule <cron> <message>   — add a recurring scheduled message
  Example: /schedule "0 9 * * *" Good morning everyone!
/schedules                   — list scheduled messages for this chat
/delschedule <id>            — delete a scheduled message
"""
import logging
import uuid
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import save_scheduled, delete_scheduled, get_all_scheduled, get_all_scheduled_all_chats
from utils import is_admin

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_bot = None


def set_scheduler(s: AsyncIOScheduler, bot):
    global _scheduler, _bot
    _scheduler = s
    _bot = bot


async def _send_scheduled(chat_id: int, message: str):
    try:
        await _bot.send_message(chat_id, message, parse_mode="HTML")
    except Exception as e:
        logger.error("Scheduled send failed for %s: %s", chat_id, e)


async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    # Expect: /schedule "cron_expr" message text
    raw = update.message.text.split(None, 1)
    if len(raw) < 2:
        return await update.message.reply_text(
            "Usage: /schedule \"cron expr\" <message>\n"
            "Example: /schedule \"0 9 * * *\" Good morning!"
        )

    rest = raw[1]
    if rest.startswith('"'):
        end_quote = rest.find('"', 1)
        if end_quote == -1:
            return await update.message.reply_text("❌ Close the cron expression with a quote.")
        cron_expr = rest[1:end_quote]
        message = rest[end_quote + 1:].strip()
    else:
        parts = rest.split(None, 1)
        cron_expr = parts[0]
        message = parts[1] if len(parts) > 1 else ""

    if not message:
        return await update.message.reply_text("❌ Message text is empty.")

    try:
        trigger = CronTrigger.from_crontab(cron_expr)
    except Exception:
        return await update.message.reply_text(
            "❌ Invalid cron expression.\n"
            "Format: min hour day month weekday\n"
            "Example: 0 9 * * * (every day at 9 AM)"
        )

    job_id = str(uuid.uuid4())[:8]
    _scheduler.add_job(
        _send_scheduled,
        trigger,
        args=[chat.id, message],
        id=job_id,
        replace_existing=True
    )
    await save_scheduled(chat.id, message, cron_expr, job_id)
    await update.message.reply_text(
        f"✅ Scheduled message added!\n"
        f"ID: <code>{job_id}</code>\n"
        f"Cron: <code>{cron_expr}</code>\n"
        f"Message: {message}",
        parse_mode="HTML"
    )


async def schedules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    rows = await get_all_scheduled(chat.id)
    if not rows:
        return await update.message.reply_text("📋 No scheduled messages.")

    lines = ["📅 <b>Scheduled Messages:</b>"]
    for row_id, msg, cron, job_id in rows:
        lines.append(f"\n• ID: <code>{job_id}</code>\n  Cron: <code>{cron}</code>\n  Msg: {msg[:60]}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def delschedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    caller = update.effective_user
    if not await is_admin(chat, caller.id):
        return await update.message.reply_text("⛔ Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /delschedule <job_id>")

    job_id = context.args[0]
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
    await delete_scheduled(job_id)
    await update.message.reply_text(f"✅ Scheduled message <code>{job_id}</code> deleted.", parse_mode="HTML")


async def restore_schedules(bot, scheduler: AsyncIOScheduler):
    """Reload all scheduled messages from DB on startup."""
    rows = await get_all_scheduled_all_chats()
    for chat_id, message, cron_expr, job_id in rows:
        try:
            trigger = CronTrigger.from_crontab(cron_expr)
            scheduler.add_job(
                _send_scheduled,
                trigger,
                args=[chat_id, message],
                id=job_id,
                replace_existing=True
            )
        except Exception as e:
            logger.warning("Failed to restore job %s: %s", job_id, e)
    logger.info("Restored %d scheduled messages", len(rows))


def register(app):
    app.add_handler(CommandHandler("schedule", schedule_cmd))
    app.add_handler(CommandHandler("schedules", schedules_cmd))
    app.add_handler(CommandHandler("delschedule", delschedule_cmd))
