from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

import tgbot.database as db


class StatsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.chat.type in ["group", "supergroup"]:
            user = event.from_user
            if user and not user.is_bot:
                chat_registered = await db.is_chat_registered(event.chat.id)
                if not chat_registered:
                    bot = data.get("bot")
                    if bot:
                        await db.register_chat_and_sync_admins(bot, event.chat.id)
                        import asyncio
                        from tgbot.userbot_sync import fetch_and_import_chat_members
                        asyncio.create_task(fetch_and_import_chat_members(event.chat.id))

                await db.log_message(
                    user_id=user.id,
                    chat_id=event.chat.id,
                    username=user.username or "",
                    full_name=user.full_name,
                )
        return await handler(event, data)
