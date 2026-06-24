"""
/start and /help command.
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

HELP_TEXT = """
🤖 <b>Group Manager Bot — Commands</b>

<b>🔨 Moderation</b>
/ban [reply/@user] [reason] — Ban a user
/unban [reply/@user] — Unban a user
/kick [reply/@user] [reason] — Kick a user
/mute [reply/@user] [duration] — Mute a user (e.g. 1h, 30m, 2d)
/unmute [reply/@user] — Unmute a user
/warn [reply/@user] [reason] — Warn a user
/unwarn [reply/@user] — Clear warnings
/warnings [reply/@user] — View warnings
/setwarn &lt;number&gt; — Set max warnings before ban

<b>🚫 Blocklist</b>
/addblock &lt;word&gt; — Block a word
/rmblock &lt;word&gt; — Remove a blocked word
/blocklist — View blocked words

<b>🌙 Night Mode</b>
/nightmode on|off — Enable/disable night mode
/nightmode set HH:MM HH:MM — Set lock/unlock times
/nightmode status — View current schedule

<b>👋 Welcome</b>
/setwelcome &lt;message&gt; — Set welcome message
  Variables: {name} {username} {chat}
/welcome on|off — Toggle welcome message

<b>📅 Scheduled Messages</b>
/schedule "cron" &lt;message&gt; — Add scheduled message
  Example: /schedule "0 9 * * *" Good morning!
/schedules — List scheduled messages
/delschedule &lt;id&gt; — Delete a scheduled message

<b>📋 Logs & Settings</b>
/setlog &lt;channel_id&gt; — Set log channel
/setlog off — Disable logging
/settings — View all settings

<b>🔒 Profile Guard</b>
Users without a name or username are automatically muted.
They are unmuted once they add a name/username.
"""


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm a group management bot.\n\nAdd me to a group and make me admin to get started.\nUse /help to see all commands.",
        parse_mode="HTML"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")


def register(app):
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
