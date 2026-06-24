"""
Telegram Group Manager Bot
Entry point — wires everything together and starts polling.

Environment variables:
  BOT_TOKEN   — required, from @BotFather
  DB_PATH     — optional, default: groupbot.db
"""
import asyncio
import logging
import os

from telegram.ext import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db
from handlers import help, moderation, blocklist, nightmode, welcome, scheduler, settings, profile_guard

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(app: Application):
    """Run after the bot is initialised — restore persistent jobs."""
    sched: AsyncIOScheduler = app.bot_data["scheduler"]

    # Give handlers access to bot + scheduler
    nightmode.set_scheduler(sched)
    scheduler.set_scheduler(sched, app.bot)

    # Restore jobs from DB
    await nightmode.restore_night_schedules(app.bot, sched)
    await scheduler.restore_schedules(app.bot, sched)

    logger.info("Bot post_init complete.")


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set!")

    # Initialise database synchronously before the event loop starts
    asyncio.get_event_loop().run_until_complete(init_db())

    # Build APScheduler
    sched = AsyncIOScheduler()
    sched.start()

    # Build Application
    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    app.bot_data["scheduler"] = sched

    # Register all handlers (order matters — profile_guard last for message handlers)
    help.register(app)
    settings.register(app)
    moderation.register(app)
    blocklist.register(app)
    nightmode.register(app)
    welcome.register(app)
    scheduler.register(app)
    profile_guard.register(app)

    logger.info("Starting bot polling…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
