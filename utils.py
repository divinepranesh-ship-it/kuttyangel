"""
Shared utility helpers.
"""
import logging
from telegram import Bot, Chat, ChatPermissions
from telegram.error import TelegramError
from database import get_settings

logger = logging.getLogger(__name__)

FULL_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=False,
)

MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)


async def is_admin(chat: Chat, user_id: int) -> bool:
    try:
        member = await chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except TelegramError:
        return False


async def send_log(bot: Bot, chat_id: int, text: str):
    """Send a log message to the configured log channel (if any)."""
    try:
        settings = await get_settings(chat_id)
        log_channel = settings.get("log_channel_id")
        if log_channel:
            await bot.send_message(chat_id=log_channel, text=text, parse_mode="HTML")
    except TelegramError as e:
        logger.warning("Log send failed: %s", e)


def mention_html(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'
