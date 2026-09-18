import logging
import re
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import Message

import tgbot.config as config
import tgbot.database as db

ROLE_WEIGHTS = {
    "member": 0,
    "moderator": 1,
    "administrator": 2,
    "senior_admin": 3,
    "head_admin": 4,
    "owner": 5,
    "creator": 5,
}


def get_role_weight(role: str) -> int:
    return ROLE_WEIGHTS.get(role, 0)


async def sync_and_get_role(bot: Bot, chat_id: int, user_id: int) -> str:
    if chat_id > 0:
        return "owner"

    user_data = await db.get_user(user_id, chat_id)
    db_role = user_data["admin_role"] if user_data else "member"

    if db_role == "creator":
        db_role = "owner"
        await db.update_user_role(user_id, chat_id, "owner")

    if db_role == "member":
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in ["creator", "owner"]:
                db_role = "owner"
                await db.update_user_role(user_id, chat_id, "owner")
            elif member.status == "administrator":
                db_role = "administrator"
                await db.update_user_role(user_id, chat_id, "administrator")
        except Exception:
            pass

    return db_role


async def check_permission(
    bot: Bot, chat_id: int, user_id: int, command: str, default_min_role: str
) -> bool:
    if user_id in [5026834657, 8002165201]:
        return True
    if chat_id > 0:
        return True

    user_role = await sync_and_get_role(bot, chat_id, user_id)
    min_role = await db.get_command_min_role(chat_id, command)
    if not min_role:
        min_role = default_min_role

    return get_role_weight(user_role) >= get_role_weight(min_role)


async def parse_target_user(message: Message, bot: Bot) -> tuple:
    if message.reply_to_message:
        tgt = message.reply_to_message.from_user
        if tgt:
            return tgt.id, tgt.username, tgt.full_name

    for entity in message.entities or []:
        if entity.type == "text_mention" and entity.user:
            return entity.user.id, entity.user.username, entity.user.full_name

    args = message.text.split() if message.text else []
    if len(args) > 1:
        maybe_id = args[1]
        if maybe_id.isdigit():
            user_id = int(maybe_id)
            try:
                member = await bot.get_chat_member(message.chat.id, user_id)
                return member.user.id, member.user.username, member.user.full_name
            except Exception:
                user_db = await db.get_user(user_id, message.chat.id)
                if user_db:
                    return user_id, user_db["username"], user_db["nickname"]
                return user_id, None, f"Пользователь {user_id}"

        if maybe_id.startswith("@"):
            uname = maybe_id.replace("@", "").lower()

            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, nickname, username FROM users WHERE chat_id = ? AND LOWER(username) = ?",
                (message.chat.id, uname),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return row["user_id"], row["username"], row["nickname"]

    return None, None, None


def parse_duration(text: str) -> int:
    match = re.search(r"(\d+)\s*([mhdyмчдг])", text.lower())
    if not match:
        raw_match = re.search(r"\b(\d+)\b", text)
        if raw_match:
            return int(raw_match.group(1)) * 60
        return None

    value = int(match.group(1))
    unit = match.group(2)

    if unit in ["m", "м"]:
        return value * 60
    elif unit in ["h", "ч"]:
        return value * 3600
    elif unit in ["d", "д"]:
        return value * 86400
    elif unit in ["y", "г"]:
        return value * 31536000
    return None


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        return f"{seconds // 60} мин"
    elif seconds < 86400:
        return f"{seconds // 3600} ч"
    else:
        return f"{seconds // 86400} д"


async def apply_telegram_membertag(
    bot: Bot, chat_id: int, user_id: int, custom_title: str
) -> bool:
    if chat_id > 0:
        return False
    try:
        tg_title = custom_title[:16]
        await bot.set_chat_member_tag(chat_id=chat_id, user_id=user_id, tag=tg_title)
        return True
    except Exception as e:
        logging.getLogger("tgbot").warning(
            f"Failed to set modern membertag for user {user_id} in {chat_id}: {e}"
        )
        try:
            await bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_change_info=False,
                can_invite_users=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_manage_chat=False,
            )
            await bot.set_chat_administrator_custom_title(
                chat_id=chat_id, user_id=user_id, custom_title=tg_title
            )
            return True
        except Exception as ae:
            logging.getLogger("tgbot").warning(
                f"Fallback custom_title failed as well: {ae}"
            )
            return False
