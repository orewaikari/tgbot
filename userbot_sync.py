import asyncio
import logging
from pyrogram import Client
import tgbot.config as config
import tgbot.database as db

logger = logging.getLogger("tgbot.userbot")

userbot_client: Client | None = None


def get_userbot_client() -> Client | None:
    global userbot_client
    if userbot_client is not None:
        return userbot_client

    if not config.API_ID or not config.API_HASH or not config.USERBOT_SESSION:
        logger.info("Pyrogram userbot parameters (API_ID, API_HASH, USERBOT_SESSION) are not fully configured.")
        return None

    try:
        api_id = int(config.API_ID)
        userbot_client = Client(
            name="tgbot_userbot",
            api_id=api_id,
            api_hash=config.API_HASH,
            session_string=config.USERBOT_SESSION,
            in_memory=True,
        )
        return userbot_client
    except Exception as e:
        logger.error(f"Failed to initialize Pyrogram userbot client: {e}")
        return None


async def start_userbot():
    client = get_userbot_client()
    if client:
        try:
            await client.start()
            me = await client.get_me()
            logger.info(f"Pyrogram userbot started successfully as @{me.username or me.id}")
        except Exception as e:
            logger.error(f"Failed to start Pyrogram userbot: {e}")


async def stop_userbot():
    global userbot_client
    if userbot_client and userbot_client.is_connected:
        try:
            await userbot_client.stop()
            logger.info("Pyrogram userbot stopped.")
        except Exception as e:
            logger.error(f"Error stopping Pyrogram userbot: {e}")


async def fetch_and_import_chat_members(chat_id: int) -> int:
    client = get_userbot_client()
    if not client or not client.is_connected:
        logger.warning(f"Pyrogram userbot is not active. Cannot auto-fetch members for chat {chat_id}")
        return 0

    try:
        logger.info(f"Starting Pyrogram userbot member fetch for chat {chat_id}...")
        users_to_import = []

        async for member in client.get_chat_members(chat_id):
            user = member.user
            if user.is_bot or user.is_deleted:
                continue

            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or f"User {user.id}"
            users_to_import.append({
                "user_id": user.id,
                "chat_id": chat_id,
                "username": user.username or "",
                "nickname": full_name,
            })

        if users_to_import:
            count = await db.bulk_register_chat_users(users_to_import)
            logger.info(f"Successfully imported {count} new members to database for chat {chat_id} (total scanned: {len(users_to_import)})")
            return count
        return 0
    except Exception as e:
        logger.error(f"Error fetching chat members with Pyrogram userbot for chat {chat_id}: {e}")
        return 0
