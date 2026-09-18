import asyncio
import logging

from aiogram import F, Router
from aiogram.types import Message

import tgbot.database as db
import tgbot.utils as utils

router = Router()
logger = logging.getLogger("tgbot")


def is_summon_admins(message: Message) -> bool:
    if not message.text:
        return False
    text = message.text.lower().strip()
    admin_triggers = [
        "созыв админов", "созвать админов", "созыв админы", "созвать админов",
        "!админы", "/admins", "!созыв админов", "!созвать админов",
        "админы", "/admins_summon", "/созыв админов", "/созвать админов", "/админы",
    ]
    return any(text.startswith(trigger) for trigger in admin_triggers)


def is_summon_all(message: Message) -> bool:
    if not message.text:
        return False
    text = message.text.lower().strip()
    all_triggers = [
        "созыв", "созвать всех", "созыв всех", "/all",
        "!созыв", "!созвать всех", "!созыв всех", "/all_summon",
        "/созыв", "/созвать всех", "/созыв всех",
    ]
    return any(text.startswith(trigger) for trigger in all_triggers)


@router.message(is_summon_admins)
async def summon_admins(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return
    chat_id = message.chat.id
    logger.info(f"summon_admins triggered by user {message.from_user.id} in chat {chat_id}")
    allowed = await utils.check_permission(message.bot, chat_id, message.from_user.id, "!админы", "member")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв для созывᴀ ᴀдминистᴘᴀции!")
        return
    admins = await db.get_chat_admins(chat_id)
    if not admins:
        await message.reply("📢 В бᴀзᴇ дᴀнных нᴇт зᴀᴘᴇгистᴘиᴘовᴀнных ᴀдминистᴘᴀтоᴘов чᴀтᴀ.")
        return
    await message.reply("🚨 *ВЫЗОВ ᴀДМИНИСТᴘᴀЦИИ ЧᴀТᴀ!* 🚨")
    mentions = []
    for admin in admins:
        name = admin["nickname"] or f"Админ {admin['user_id']}"
        mentions.append(f"[{name}](tg://user?id={admin['user_id']})")
    text = "⚠️ " + ", ".join(mentions)
    await message.answer(text, parse_mode="Markdown")


@router.message(
    F.text.lower().in_([
        "!обновить_базу", "обновить базу", "!чистка_базы", "чистка базы", "/clean_db"
    ])
)
async def manual_cleanup_users(message: Message):
    allowed = await utils.check_permission(
        message.bot, message.chat.id, message.from_user.id, "!чистка_базы", "administrator"
    )
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв ᴀдминистᴘᴀтоᴘᴀ для зᴀпʏскᴀ чистки бᴀзы дᴀнных!")
        return
    chat_id = message.chat.id
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return
    msg = await message.reply("🔍 Зᴀпʏскᴀю пᴘовᴇᴘкʏ и чисткʏ нᴇᴀктивных/вышᴇдших ʏчᴀстников... Пожᴀлʏйстᴀ, подождитᴇ.")

    users = await db.get_all_chat_users(chat_id)
    if not users:
        await msg.edit_text("❌ В бᴀзᴇ дᴀнных этого чᴀтᴀ нᴇт зᴀᴘᴇгистᴘиᴘовᴀнных пользовᴀтᴇлᴇй.")
        return
    removed_count = 0
    checked_count = 0
    for u in users:
        user_id = u["user_id"]
        checked_count += 1
        try:
            member = await message.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
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
    await msg.edit_text(
        f"✅ Проверка завершена!\n\n📊 Проверено пользователей: *{checked_count}*\n🧹 Удалено из базы (вышли или забанены): *{removed_count}*",
        parse_mode="Markdown",
    )


@router.message(
    F.text.lower().in_([
        "!добор", "!автодобор", "добор", "автодобор", "/dobor", "/sync_members"
    ])
)
async def manual_dobor_users(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return
    allowed = await utils.check_permission(
        message.bot, message.chat.id, message.from_user.id, "!добор", "administrator"
    )
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв ᴀдминистᴘᴀтоᴘᴀ для зᴀпʏскᴀ ᴀвтодобоᴘᴀ ʏчᴀстников!")
        return

    msg = await message.reply("🔄 Зᴀпʏскᴀю ᴀвтодобоᴘ всᴇх ʏчᴀстников бᴇсᴇды чᴇᴘᴇз Userbot... Пожᴀлʏйстᴀ, подождитᴇ.")

    from tgbot.userbot_sync import fetch_and_import_chat_members
    count = await fetch_and_import_chat_members(message.chat.id)

    if count > 0:
        await msg.edit_text(
            f"✅ Автодобор успешно завершен!\n\n📥 В базу данных добавлено новых участников: *{count}*",
            parse_mode="Markdown",
        )
    else:
        await msg.edit_text(
            "ℹ️ Все участники беседы уже внесены в базу данных, либо Юзербот не настроен/не состоит в этой беседе.",
            parse_mode="Markdown",
        )


@router.message(is_summon_all)
async def summon_all(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return
    chat_id = message.chat.id
    logger.info(f"summon_all triggered by user {message.from_user.id} in chat {chat_id}")

    allowed = await utils.check_permission(message.bot, chat_id, message.from_user.id, "!созыв", "member")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв для созывᴀ ʏчᴀстников!")
        return
    users = await db.get_all_chat_users(chat_id)

    active_users = [u for u in users if u["user_id"] != message.from_user.id]
    if not active_users:
        await message.reply("📢 Созывᴀть нᴇкого! Вы ᴇдинствᴇнный ᴀктивный ʏчᴀстник.")
        return
    await message.reply("📣 *ОБЩИЙ СБОᴘ ЧᴀТᴀ!* 📣")

    batch_size = 10
    for i in range(0, len(active_users), batch_size):
        batch = active_users[i : i + batch_size]
        mentions = []
        for u in batch:
            name = u["nickname"] or f"Участник {u['user_id']}"
            mentions.append(f"[{name}](tg://user?id={u['user_id']})")
        text = "🔔 " + ", ".join(mentions)
        await message.answer(text, parse_mode="Markdown")
