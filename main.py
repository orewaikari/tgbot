import asyncio
import logging
import re
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import tgbot.config as config
import tgbot.database as db
from tgbot.handlers import (
    admin,
    fun,
    games,
    registration,
    stats,
    stt,
    whisper,
    zazyvala,
)
from tgbot.middlewares.stats_middleware import StatsMiddleware

_original_bot_call = Bot.__call__
_url_pattern = re.compile(r"(https?://\S+|tg://\S+)")

_cyrillic_map = {
    "\u0415": "ᴇ",
    "\u0435": "ᴇ",
    "\u0423": "ʏ",
    "\u0443": "ʏ",
    "\u0410": "ᴀ",
    "\u0430": "ᴀ",
    "\u0420": "ᴘ",
    "\u0440": "ᴘ",
}

_user_facing_fields = {"text", "caption", "title", "description", "message_text"}


def _replace_letters(text: str) -> str:
    if not isinstance(text, str):
        return text
    chars = list(text)
    for i, c in enumerate(chars):
        if c in _cyrillic_map:
            chars[i] = _cyrillic_map[c]
    return "".join(chars)


def _lower_except_urls(text: str) -> str:
    urls = _url_pattern.findall(text)
    if not urls:
        return text.lower()
    parts = _url_pattern.split(text)
    for i, part in enumerate(parts):
        if not _url_pattern.match(part):
            parts[i] = part.lower()
    return "".join(parts)


def _deep_replace_strings(obj, field_name=None):
    if isinstance(obj, str):
        if field_name in _user_facing_fields:
            return _replace_letters(_lower_except_urls(obj))
        return obj
    elif isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = _deep_replace_strings(v, field_name=k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = _deep_replace_strings(v, field_name=field_name)
    elif hasattr(obj, "__class__") and hasattr(obj.__class__, "model_fields"):
        for f_name in obj.__class__.model_fields.keys():
            try:
                val = getattr(obj, f_name)
                if val is not None:
                    setattr(obj, f_name, _deep_replace_strings(val, field_name=f_name))
            except Exception:
                pass
    elif hasattr(obj, "__dict__"):
        for k, v in list(obj.__dict__.items()):
            if not k.startswith("_"):
                try:
                    setattr(obj, k, _deep_replace_strings(v, field_name=k))
                except Exception:
                    pass
    return obj


async def _patched_bot_call(self, method, *args, **kwargs):
    try:
        method = _deep_replace_strings(method)
    except Exception as e:
        logging.getLogger("tgbot").error(f"Error in deep_replace_strings patch: {e}")
    return await _original_bot_call(self, method, *args, **kwargs)


Bot.__call__ = _patched_bot_call

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("tgbot")


async def weekly_quota_cleanup_task(bot: Bot):
    logger.info("Weekly quota cleanup background task started.")
    while True:
        try:
            now = datetime.now()

            if now.isoweekday() == 7 and now.hour == 20 and now.minute == 0:
                current_iso_week = f"{now.year}-{now.isocalendar()[1]}"
                last_cleanup = await db.get_reg_setting("last_weekly_cleanup_week")

                if last_cleanup != current_iso_week:
                    logger.info("Starting weekly quota cleanup...")
                    await db.set_reg_setting("last_weekly_cleanup_week", current_iso_week)

                    private_chat_id = await db.get_reg_setting("private_chat_id")
                    admin_chat_id = await db.get_reg_setting("admin_chat_id")

                    if private_chat_id:
                        p_chat_id = int(private_chat_id)
                        users = await db.get_all_chat_users(p_chat_id)

                        kicked_users_reports = []

                        for user in users:
                            user_id = user["user_id"]
                            nickname = user["nickname"] or user["username"] or f"ID {user_id}"

                            try:
                                member = await bot.get_chat_member(p_chat_id, user_id)
                                if member.status in ["creator", "administrator"]:
                                    continue
                            except Exception:
                                pass

                            rest_until_str = user.get("rest_until")
                            if rest_until_str:
                                try:
                                    rest_until = datetime.fromisoformat(rest_until_str)
                                    if datetime.now() < rest_until:
                                        logger.info(
                                            f"Skipping user {nickname} ({user_id}) from cleanup: user is on rest until {rest_until_str}"
                                        )
                                        continue
                                except Exception as e:
                                    logger.error(f"Error parsing rest_until for user {user_id}: {e}")

                            msg_week = user.get("messages_week") or 0
                            if msg_week < 100:
                                try:
                                    freed_chars = await db.free_character_by_user_id(user_id)
                                    char_names = [c["name"] for c in freed_chars] if freed_chars else []
                                    char_str = f" (персонаж: {', '.join(char_names)})" if char_names else ""

                                    await bot.ban_chat_member(chat_id=p_chat_id, user_id=user_id)
                                    await bot.unban_chat_member(chat_id=p_chat_id, user_id=user_id)

                                    kicked_users_reports.append(f"• {nickname}{char_str} — {msg_week} сообщ.")
                                except Exception as e:
                                    logger.error(f"Failed to kick user {user_id}: {e}")

                        if kicked_users_reports:
                            report_text = (
                                "🧹 *ЕЖЕНЕДЕЛЬНАЯ ОЧИСТКА НЕАКТИВНЫХ УЧАСТНИКОВ* 🧹\n\n"
                                "Следующие участники были исключены из чата за недобор недельной нормы активности (< 100 сообщений):\n"
                                + "\n".join(kicked_users_reports)
                                + "\n\n"
                                "🚪 Их выбранные персонажи были освобождены!"
                            )
                        else:
                            report_text = (
                                "🧹 *ЕЖЕНЕДЕЛЬНАЯ ОЧИСТКА НЕАКТИВНЫХ УЧАСТНИКОВ* 🧹\n\n"
                                "Все участники выполнили недельную норму активности (>= 100 сообщений)! "
                                "Никто не был исключен. Отличная работа! 🎉"
                            )

                        try:
                            await bot.send_message(chat_id=p_chat_id, text=report_text, parse_mode="Markdown")
                        except Exception as e:
                            logger.error(f"Failed to send weekly report to game chat: {e}")

                        if admin_chat_id:
                            try:
                                await bot.send_message(
                                    chat_id=int(admin_chat_id), text=report_text, parse_mode="Markdown"
                                )
                            except Exception as e:
                                logger.error(f"Failed to send weekly report to admin chat: {e}")

            if now.isoweekday() == 7 and now.hour == 12 and now.minute == 10:
                current_iso_week = f"{now.year}-{now.isocalendar()[1]}"
                last_reward = await db.get_reg_setting("last_weekly_reward_week")
                if last_reward != current_iso_week:
                    logger.info("Starting weekly activity reward...")
                    await db.set_reg_setting("last_weekly_reward_week", current_iso_week)
                    private_chat_id = await db.get_reg_setting("private_chat_id")
                    if private_chat_id:
                        p_chat_id = int(private_chat_id)
                        top_users = await db.get_top_active(p_chat_id, order_by="messages_week", limit=1)
                        if top_users and (top_users[0].get("messages_week") or 0) > 0:
                            top_user = top_users[0]
                            user_id = top_user["user_id"]
                            nickname = top_user["nickname"] or top_user["username"] or f"ID {user_id}"
                            msg_count = top_user["messages_week"] or 0

                            await db.add_coins(user_id, p_chat_id, 2000)
                            congrats_text = (
                                "🎉 *НАГРАДА ЗА АКТИВНОСТЬ ЗА НЕДЕЛЮ* 🎉\n\n"
                                f"🏆 Самым активным участником чата на этой неделе становится *{nickname}*!\n"
                                f"📊 Количество отправленных сообщений: *{msg_count}*\n\n"
                                f"💰 За проявленную активность вы получаете награду в размере *2000* монет! 🪙"
                            )
                            try:
                                await bot.send_message(chat_id=p_chat_id, text=congrats_text, parse_mode="Markdown")
                            except Exception as e:
                                logger.error(f"Failed to send weekly reward message to chat {p_chat_id}: {e}")

            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Error in weekly quota cleanup task: {e}")
            await asyncio.sleep(60)


async def periodic_left_member_cleanup_task(bot: Bot):
    logger.info("Periodic left-member cleanup background task started.")

    try:
        logger.info("Running initial startup sweep to clean up left members...")
        records = await db.get_all_users_to_verify()
        if records:
            removed_count = 0
            for record in records:
                user_id = record["user_id"]
                chat_id = record["chat_id"]
                if chat_id > 0:
                    continue
                try:
                    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                    if member.status in ["left", "kicked"]:
                        await db.remove_user_from_chat(user_id, chat_id)
                        removed_count += 1
                except Exception as e:
                    err_msg = str(e).lower()
                    if (
                        "user not found" in err_msg
                        or "chat not found" in err_msg
                        or "chat_write_forbidden" in err_msg
                        or "invalid" in err_msg
                    ):
                        await db.remove_user_from_chat(user_id, chat_id)
                        removed_count += 1
                await asyncio.sleep(0.05)
            if removed_count > 0:
                logger.info(f"Startup sweep completed. Removed {removed_count} left members.")
    except Exception as e:
        logger.error(f"Error during startup sweep: {e}")

    while True:
        try:
            await asyncio.sleep(4 * 3600)
            logger.info("Running periodic sweep to clean up left members...")

            records = await db.get_all_users_to_verify()
            if not records:
                continue

            removed_count = 0
            for record in records:
                user_id = record["user_id"]
                chat_id = record["chat_id"]

                if chat_id > 0:
                    continue

                try:
                    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                    if member.status in ["left", "kicked"]:
                        await db.remove_user_from_chat(user_id, chat_id)
                        removed_count += 1
                        logger.info(f"Sweep removed user {user_id} from chat {chat_id}")
                except Exception as e:
                    err_msg = str(e).lower()

                    if (
                        "user not found" in err_msg
                        or "chat not found" in err_msg
                        or "chat_write_forbidden" in err_msg
                        or "invalid" in err_msg
                    ):
                        await db.remove_user_from_chat(user_id, chat_id)
                        removed_count += 1
                        logger.info(f"Sweep removed user {user_id} from chat {chat_id} due to API error: {e}")

                await asyncio.sleep(0.1)

            if removed_count > 0:
                logger.info(f"Periodic sweep completed. Removed {removed_count} left members.")
        except Exception as e:
            logger.error(f"Error in periodic left-member cleanup task: {e}")
            await asyncio.sleep(60)


async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN is not configured! Please set it in tgbot/.env and restart.")
        return
    logger.info("Starting Telegram Bot...")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    asyncio.create_task(weekly_quota_cleanup_task(bot))
    asyncio.create_task(periodic_left_member_cleanup_task(bot))
    dp = Dispatcher()

    dp.message.outer_middleware(StatsMiddleware())

    dp.include_router(registration.router)
    dp.include_router(admin.router)
    dp.include_router(stats.router)
    dp.include_router(zazyvala.router)
    dp.include_router(whisper.router)
    dp.include_router(stt.router)
    dp.include_router(fun.router)
    dp.include_router(games.router)

    await bot.delete_webhook(drop_pending_updates=True)

    from tgbot.userbot_sync import start_userbot, stop_userbot
    await start_userbot()

    logger.info("Bot is successfully running! Polling starts now...")
    try:
        allowed_updates = dp.resolve_used_update_types()
        if "chat_member" not in allowed_updates:
            allowed_updates.append("chat_member")
        await dp.start_polling(bot, allowed_updates=allowed_updates)
    finally:
        await stop_userbot()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot has been stopped.")
