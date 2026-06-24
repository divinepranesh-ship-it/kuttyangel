"""
Profile Guard — mutes users who have no first name AND no username.
On every message, checks the sender. If they have no name/username:
  - Mute them
  - DM them instructions
  - When they update their profile and send a message, they are automatically unmuted.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, ChatMemberHandler, filters
from telegram.error import TelegramError

from database import add_muted_no_profile, remove_muted_no_profile, is_muted_no_profile
from utils import MUTE_PERMISSIONS, FULL_PERMISSIONS, send_log, mention_html, is_admin

logger = logging.getLogger(__name__)


def _has_valid_profile(user) -> bool:
    """Returns True if the user has at least a first name or a username."""
    has_name = bool(user.first_name and user.first_name.strip())
    has_username = bool(user.username)
    return has_name or has_username


async def check_profile_on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not user or not msg:
        return
    if await is_admin(chat, user.id):
        return

    already_muted = await is_muted_no_profile(chat.id, user.id)

    if not _has_valid_profile(user):
        if not already_muted:
            # Mute them
            try:
                await chat.restrict_member(user.id, MUTE_PERMISSIONS)
                await add_muted_no_profile(chat.id, user.id)
                notice = await msg.reply_text(
                    f"🔇 {mention_html(user.id, user.full_name or 'User')}, you have been muted because "
                    f"you don't have a <b>first name</b> or <b>username</b> set on your Telegram account.\n\n"
                    f"Please set a name or username in your Telegram settings, then send any message here "
                    f"to be automatically unmuted.",
                    parse_mode="HTML"
                )
                await send_log(context.bot, chat.id,
                               f"🔇 PROFILE MUTE | Chat: {chat.title}\n"
                               f"User ID: {user.id} — no name/username")
                # Try to DM them
                try:
                    await context.bot.send_message(
                        user.id,
                        f"You have been muted in <b>{chat.title}</b> because your Telegram account "
                        f"has no first name or username.\n\n"
                        f"To unmute:\n1. Go to Telegram Settings → Edit Profile\n"
                        f"2. Add a first name or username\n"
                        f"3. Send any message in the group",
                        parse_mode="HTML"
                    )
                except TelegramError:
                    pass  # User may have DMs blocked
            except TelegramError as e:
                logger.error("Profile mute failed: %s", e)
    else:
        # They now have a valid profile — unmute if they were muted for this reason
        if already_muted:
            try:
                await chat.restrict_member(user.id, FULL_PERMISSIONS)
                await remove_muted_no_profile(chat.id, user.id)
                await msg.reply_text(
                    f"✅ Welcome back, {mention_html(user.id, user.full_name)}! "
                    f"You have been unmuted. Enjoy the chat!",
                    parse_mode="HTML"
                )
                await send_log(context.bot, chat.id,
                               f"✅ PROFILE UNMUTE | Chat: {chat.title}\n"
                               f"User: {mention_html(user.id, user.full_name)}")
            except TelegramError as e:
                logger.error("Profile unmute failed: %s", e)


async def check_profile_on_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Also check when a new member joins."""
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not msg.new_chat_members:
        return

    for member in msg.new_chat_members:
        if member.is_bot:
            continue
        if not _has_valid_profile(member):
            try:
                await chat.restrict_member(member.id, MUTE_PERMISSIONS)
                await add_muted_no_profile(chat.id, member.id)
                await msg.reply_text(
                    f"👋 Welcome {mention_html(member.id, member.full_name or 'new member')}!\n"
                    f"🔇 You have been muted because your account has no <b>name</b> or <b>username</b>.\n"
                    f"Please update your Telegram profile and send a message here to be unmuted.",
                    parse_mode="HTML"
                )
            except TelegramError as e:
                logger.error("Join profile mute failed: %s", e)


def register(app):
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        check_profile_on_message,
        block=False
    ))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        check_profile_on_join,
        block=False
    ))
