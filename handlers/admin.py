import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import ChatPermissions, Message

import tgbot.database as db
import tgbot.utils as utils

router = Router()


async def check_bot_admin(message: Message) -> bool:
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.bot.id)
        if member.status in ["administrator", "creator"] and member.can_restrict_members:
            return True
    except Exception:
        pass
    await message.reply("❌ Бот должᴇн быть ᴀдминистᴘᴀтоᴘом с пᴘᴀвᴀми огᴘᴀничᴇния пользовᴀтᴇлᴇй для выполнᴇния этой комᴀнды!")
    return False


async def send_audit_log(bot, action_text: str, current_chat_id: int):
    admin_chat_id = await db.get_reg_setting("admin_chat_id")
    if admin_chat_id:
        try:
            admin_chat_id_int = int(admin_chat_id)
            if current_chat_id != admin_chat_id_int:
                await bot.send_message(
                    chat_id=admin_chat_id_int,
                    text=action_text,
                    parse_mode="Markdown",
                    message_thread_id=102,
                )
        except Exception as e:
            logging.getLogger("tgbot").error(f"Failed to forward audit log: {e}")


@router.message(F.text.lower() == "правила" or F.text == "/rules")
async def show_rules(message: Message):
    rules = await db.get_chat_rules(message.chat.id)
    if not rules:
        await message.reply("📝 В этом чᴀтᴇ пᴘᴀвилᴀ покᴀ нᴇ ʏстᴀновлᴇны.")
    else:
        await message.reply(f"📜 *ПРАВИЛА ЧАТА:*\n\n{rules}", parse_mode="Markdown")


@router.message(F.text.lower().startswith("+правила") | F.text.lower().startswith("!установить правила"))
async def set_rules(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return
    allowed = await utils.check_permission(
        message.bot, message.chat.id, message.from_user.id, "+правила", "administrator"
    )
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв ᴀдминистᴘᴀтоᴘᴀ для измᴇнᴇния пᴘᴀвил!")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        parts = message.text.split(" пᴘᴀвилᴀ ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await message.reply("❌ Пожᴀлʏйстᴀ, нᴀпишитᴇ тᴇкст пᴘᴀвил послᴇ комᴀнды. Пᴘимᴇᴘ:\n`+пᴘᴀвилᴀ Нᴇ флʏдить, ʏвᴀжᴀть дᴘʏг дᴘʏгᴀ`")
        return
    rules_text = parts[1].strip()
    await db.set_chat_rules(message.chat.id, rules_text)

    moderator_name = message.from_user.full_name
    chat_title = message.chat.title or f"ID {message.chat.id}"
    log_msg = f"🛡️ *АУДИТ:* Администратор *{moderator_name}* изменил правила в чате *{chat_title}*:\n\n`{rules_text}`"
    await send_audit_log(message.bot, log_msg, message.chat.id)

    await message.reply("✅ *Пᴘᴀвилᴀ чᴀтᴀ ʏспᴇшно обновлᴇны!*", parse_mode="Markdown")


@router.message(F.text.lower().startswith("+тг тег") | F.text.lower().startswith("!тег"))
async def set_user_tag(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return
    if message.text.lower().startswith("+тг тег"):
        text_parts = message.text.lower().split("тᴇг", 1)
        tag_text = text_parts[1].strip() if len(text_parts) > 1 else ""
    else:
        parts = message.text.split(maxsplit=1)
        tag_text = parts[1].strip() if len(parts) > 1 else ""
    if not tag_text:
        await message.reply("❌ Пожᴀлʏйстᴀ, нᴀпишитᴇ тᴇкст тᴇгᴀ послᴇ комᴀнды! Пᴘимᴇᴘ:\n`+тг тᴇг Солнышко`")
        return
    if message.reply_to_message:
        allowed = await utils.check_permission(
            message.bot, message.chat.id, message.from_user.id, "+тг тег", "moderator"
        )
        if not allowed:
            await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв модᴇᴘᴀтоᴘᴀ для выдᴀчи тᴇгов дᴘʏгим ʏчᴀстникᴀм!")
            return
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name
    else:
        target_id = message.from_user.id
        target_name = message.from_user.full_name
    await db.update_user_title(target_id, message.chat.id, tag_text)

    tg_status = ""
    if await utils.apply_telegram_membertag(message.bot, message.chat.id, target_id, tag_text):
        tg_status = " (ʏспᴇшно пᴘимᴇнᴇн в Telegram)"
    else:
        tg_status = " (сохᴘᴀнᴇн в бᴀзᴇ дᴀнных; пᴘимᴇнить в Telegram нᴇ ʏдᴀлось)"

    moderator_name = message.from_user.full_name
    chat_title = message.chat.title or f"ID {message.chat.id}"
    log_msg = f"🛡️ *АУДИТ:* Модератор *{moderator_name}* установил тег для *{target_name}* в чате *{chat_title}*: *{tag_text}*{tg_status}"
    await send_audit_log(message.bot, log_msg, message.chat.id)
    await message.reply(f"✅ Для *{target_name}* установлен тег: *{tag_text}*{tg_status}", parse_mode="Markdown")


@router.message(
    F.text.lower().startswith("+модер")
    | F.text.lower().startswith("-модер")
    | F.text.lower().startswith("+админ")
    | F.text.lower().startswith("-админ")
    | F.text.lower().startswith("+ст_админ")
    | F.text.lower().startswith("-ст_админ")
    | F.text.lower().startswith("+стадмин")
    | F.text.lower().startswith("-стадмин")
    | F.text.lower().startswith("+гл_админ")
    | F.text.lower().startswith("-гл_админ")
    | F.text.lower().startswith("+гладмин")
    | F.text.lower().startswith("-гладмин")
    | F.text.lower().startswith("+владелец")
    | F.text.lower().startswith("-владелец")
    | F.text.lower().startswith("+owner")
    | F.text.lower().startswith("-owner")
    | F.text.lower().startswith("+старший администратор")
    | F.text.lower().startswith("-старший администратор")
    | F.text.lower().startswith("+главный администратор")
    | F.text.lower().startswith("-главный администратор")
    | F.text.lower().startswith("+старший_администратор")
    | F.text.lower().startswith("-старший_администратор")
    | F.text.lower().startswith("+главный_администратор")
    | F.text.lower().startswith("-главный_администратор")
)
async def promote_demote(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return
    text = message.text.lower()
    is_promote = text.startswith("+")

    if "владелец" in text or "owner" in text:
        target_assigned_role = "owner"
        role_label = "Влᴀдᴇлᴇц 👑"
    elif "гл_админ" in text or "гладмин" in text or "главный администратор" in text or "главный_администратор" in text:
        target_assigned_role = "head_admin"
        role_label = "Глᴀвный ᴀдминистᴘᴀтоᴘ 🛡️"
    elif "ст_админ" in text or "стадмин" in text or "старший администратор" in text or "старший_администратор" in text:
        target_assigned_role = "senior_admin"
        role_label = "Стᴀᴘший ᴀдминистᴘᴀтоᴘ 🎖️"
    elif "администратор" in text or "админ" in text:
        target_assigned_role = "administrator"
        role_label = "ᴀдминистᴘᴀтоᴘ 👮"
    elif "модератор" in text or "модер" in text:
        target_assigned_role = "moderator"
        role_label = "Модᴇᴘᴀтоᴘ ⚔️"
    else:
        target_assigned_role = "member"
        role_label = "ʏчᴀстник 👤"

    assigned_role = target_assigned_role if is_promote else "member"
    assigned_role_label = role_label if is_promote else "ʏчᴀстник 👤"

    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ или ʏпомянʏв @username)!")
        return
    if target_id == message.from_user.id:
        await message.reply("❌ Вы нᴇ можᴇтᴇ измᴇнять собствᴇнный ᴘᴀнг!")
        return

    promoter_role = await utils.sync_and_get_role(message.bot, message.chat.id, message.from_user.id)
    target_current_role = await utils.sync_and_get_role(message.bot, message.chat.id, target_id)
    promoter_weight = utils.get_role_weight(promoter_role)
    target_current_weight = utils.get_role_weight(target_current_role)
    assigned_weight = utils.get_role_weight(assigned_role)

    role_translations = {
        "member": "ʏчᴀстник 👤",
        "moderator": "Модᴇᴘᴀтоᴘ ⚔️",
        "administrator": "ᴀдминистᴘᴀтоᴘ 👮",
        "senior_admin": "Стᴀᴘший ᴀдминистᴘᴀтоᴘ 🎖️",
        "head_admin": "Глᴀвный ᴀдминистᴘᴀтоᴘ 🛡️",
        "owner": "Влᴀдᴇлᴇц 👑",
        "creator": "Влᴀдᴇлᴇц 👑",
    }

    if promoter_weight <= target_current_weight:
        await message.reply("❌ Вы нᴇ можᴇтᴇ измᴇнять ᴘᴀнг пользовᴀтᴇля с ᴘᴀвным или болᴇᴇ высоким стᴀтʏсом!")
        return

    if promoter_weight <= assigned_weight:
        promoter_role_ru = role_translations.get(promoter_role, promoter_role)
        await message.reply(f"❌ Вы не можете выдать роль равную или выше вашей собственной (*{promoter_role_ru}*)!")
        return

    await db.update_user_role(target_id, message.chat.id, assigned_role)

    moderator_name = message.from_user.full_name
    chat_title = message.chat.title or f"ID {message.chat.id}"
    log_msg = f"🛡️ *АУДИТ:* {moderator_name} изменил ранг для *{target_name}* в чате *{chat_title}* на *{assigned_role_label}*"
    await send_audit_log(message.bot, log_msg, message.chat.id)
    await message.reply(f"✅ Пользователь *{target_name}* теперь имеет ранг: *{assigned_role_label}*", parse_mode="Markdown")


@router.message(F.text.lower().startswith("!дк") | F.text.lower().startswith("/dk"))
async def set_command_permissions(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return

    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!дк", "head_admin")
    if not allowed:
        await message.reply("❌ Только Влᴀдᴇлᴇц или Глᴀвный ᴀдминистᴘᴀтоᴘ могʏт нᴀстᴘᴀивᴀть достʏп к комᴀндᴀм (ДК)!")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.reply(
            "❌ Нᴇвᴇᴘный фоᴘмᴀт! Пᴘимᴇᴘ использовᴀния:\n"
            "`!дк !созыв стᴀᴘший ᴀдминистᴘᴀтоᴘ` — ᴘᴀзᴘᴇшить созывᴀть всᴇх только стᴀᴘшим ᴀдминистᴘᴀтоᴘᴀм и вышᴇ.\n"
            "Достʏпныᴇ ᴘоли: `ʏчᴀстник`, `модᴇᴘᴀтоᴘ`, `ᴀдминистᴘᴀтоᴘ`, `стᴀᴘший ᴀдминистᴘᴀтоᴘ`, `глᴀвный ᴀдминистᴘᴀтоᴘ`, `влᴀдᴇлᴇц`"
        )
        return
    target_cmd = args[1].lower()

    target_role_raw = " ".join(args[2:]).lower()
    role_map = {
        "участник": "member",
        "member": "member",
        "модератор": "moderator",
        "модᴇᴘ": "moderator",
        "moderator": "moderator",
        "администратор": "administrator",
        "ᴀдмин": "administrator",
        "administrator": "administrator",
        "старший администратор": "senior_admin",
        "старший_администратор": "senior_admin",
        "ст_ᴀдмин": "senior_admin",
        "senior_admin": "senior_admin",
        "главный администратор": "head_admin",
        "главный_администратор": "head_admin",
        "гл_ᴀдмин": "head_admin",
        "head_admin": "head_admin",
        "владелец": "owner",
        "owner": "owner",
    }
    mapped_role = role_map.get(target_role_raw)
    if not mapped_role and len(args) >= 3:
        mapped_role = role_map.get(args[2].lower())
    if not mapped_role:
        await message.reply(
            "❌ Нᴇизвᴇстнᴀя ᴘоль! Допʏстимыᴇ ᴘоли:\n"
            "• `ʏчᴀстник`\n"
            "• `модᴇᴘᴀтоᴘ`\n"
            "• `ᴀдминистᴘᴀтоᴘ`\n"
            "• `стᴀᴘший ᴀдминистᴘᴀтоᴘ`\n"
            "• `глᴀвный ᴀдминистᴘᴀтоᴘ`\n"
            "• `влᴀдᴇлᴇц`"
        )
        return

    role_labels = {
        "member": "ʏчᴀстник 👤",
        "moderator": "Модᴇᴘᴀтоᴘ ⚔️",
        "administrator": "ᴀдминистᴘᴀтоᴘ 👮",
        "senior_admin": "Стᴀᴘший ᴀдминистᴘᴀтоᴘ 🎖️",
        "head_admin": "Глᴀвный ᴀдминистᴘᴀтоᴘ 🛡️",
        "owner": "Влᴀдᴇлᴇц 👑",
    }
    role_display = role_labels.get(mapped_role, mapped_role)
    await db.set_command_min_role(message.chat.id, target_cmd, mapped_role)

    moderator_name = message.from_user.full_name
    chat_title = message.chat.title or f"ID {message.chat.id}"
    log_msg = f"🛡️ *АУДИТ:* {moderator_name} изменил доступ к команде *{target_cmd}* в чате *{chat_title}* на роль *{role_display}* и выше"
    await send_audit_log(message.bot, log_msg, message.chat.id)
    await message.reply(f"✅ Доступ к команде *{target_cmd}* теперь открыт для роли *{role_display}* и выше!", parse_mode="Markdown")


@router.message(F.text.lower().startswith("!мут") | F.text.lower().startswith("/mute"))
async def mute_user(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await check_bot_admin(message):
        return

    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!мут", "moderator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв модᴇᴘᴀтоᴘᴀ для выдᴀчи мʏтᴀ!")
        return

    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ или ʏпомянʏв @username)!")
        return

    user_role = await utils.sync_and_get_role(message.bot, message.chat.id, message.from_user.id)
    target_role = await utils.sync_and_get_role(message.bot, message.chat.id, target_id)
    if utils.get_role_weight(target_role) >= utils.get_role_weight(user_role) and message.from_user.id != message.chat.id:
        await message.reply("❌ Вы нᴇ можᴇтᴇ зᴀглʏшить пользовᴀтᴇля с ᴘᴀвным или болᴇᴇ высоким ᴘᴀнгом!")
        return

    args = message.text.split()
    duration_secs = None
    reason = "Нᴇ ʏкᴀзᴀнᴀ"

    for arg in args[1:]:
        sec = utils.parse_duration(arg)
        if sec:
            duration_secs = sec
            reason_parts = [x for x in args[1:] if x != arg]
            if reason_parts:
                reason = " ".join(reason_parts)
            break

    if not duration_secs:
        duration_secs = 15 * 60
        if len(args) > 1:
            reason = " ".join(args[1:])

    until_date = datetime.now() + timedelta(seconds=duration_secs)

    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_polls=False,
        can_send_other_messages=False,
    )

    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            permissions=permissions,
            until_date=until_date,
        )
        duration_str = utils.format_duration(duration_secs)

        moderator_name = message.from_user.full_name
        chat_title = message.chat.title or f"ID {message.chat.id}"
        log_msg = f"🛡️ *АУДИТ:* Модератор *{moderator_name}* заглушил *{target_name}* в чате *{chat_title}* на *{duration_str}*.\n📝 *Причина:* {reason}"
        await send_audit_log(message.bot, log_msg, message.chat.id)
        await message.reply(
            f"🤐 *{target_name}* заглушен на *{duration_str}*.\n"
            f"📝 *Причина:* {reason}",
            parse_mode="Markdown",
        )
    except Exception as e:
        await message.reply(f"❌ Не удалось выдать мут: {e}")


@router.message(F.text.lower().startswith("!размут") | F.text.lower().startswith("/unmute"))
async def unmute_user(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await check_bot_admin(message):
        return

    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!размут", "moderator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв модᴇᴘᴀтоᴘᴀ для ᴘᴀзмʏтᴀ!")
        return

    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ или ʏпомянʏв @username)!")
        return

    permissions = ChatPermissions(
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
        can_invite_users=True,
    )

    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id, user_id=target_id, permissions=permissions
        )

        moderator_name = message.from_user.full_name
        chat_title = message.chat.title or f"ID {message.chat.id}"
        log_msg = f"🛡️ *АУДИТ:* Модератор *{moderator_name}* снял мут с *{target_name}* в чате *{chat_title}*."
        await send_audit_log(message.bot, log_msg, message.chat.id)
        await message.reply(f"🔊 *{target_name}* успешно разглушен!", parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"❌ Не удалось снять ограничения: {e}")


@router.message(F.text.lower().startswith("!варн") | F.text.lower().startswith("/warn"))
async def warn_user(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await check_bot_admin(message):
        return

    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!варн", "moderator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв модᴇᴘᴀтоᴘᴀ для выдᴀчи вᴀᴘнов!")
        return

    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ или ʏпомянʏв @username)!")
        return

    user_role = await utils.sync_and_get_role(message.bot, message.chat.id, message.from_user.id)
    target_role = await utils.sync_and_get_role(message.bot, message.chat.id, target_id)
    if utils.get_role_weight(target_role) >= utils.get_role_weight(user_role) and message.from_user.id != message.chat.id:
        await message.reply("❌ Вы нᴇ можᴇтᴇ выдᴀть пᴘᴇдʏпᴘᴇждᴇниᴇ пользовᴀтᴇлю с ᴘᴀвным или болᴇᴇ высоким ᴘᴀнгом!")
        return

    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нᴇ ʏкᴀзᴀнᴀ"

    warns_count = await db.add_warn(message.chat.id, target_id)

    moderator_name = message.from_user.full_name
    chat_title = message.chat.title or f"ID {message.chat.id}"
    if warns_count >= 3:
        try:
            await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target_id)
            await message.bot.unban_chat_member(chat_id=message.chat.id, user_id=target_id)
            await db.reset_warns(message.chat.id, target_id)

            log_msg = f"🚨 *АУДИТ:* Модератор *{moderator_name}* выдал варн {warns_count}/3 для *{target_name}* в чате *{chat_title}* за причину: `{reason}`. Пользователь был *ИСКЛЮЧЕН* из-за лимита предупреждений!"
            await send_audit_log(message.bot, log_msg, message.chat.id)
            await message.reply(
                f"🚨 *{target_name}* получил третье предупреждение и был *исключен* из чата!\n"
                f"📝 *Последняя причина:* {reason}",
                parse_mode="Markdown",
            )
        except Exception as e:
            await message.reply(f"❌ Пользователь набрал {warns_count}/3 варнов, но не удалось его исключить: {e}")
    else:
        log_msg = f"⚠️ *АУДИТ:* Модератор *{moderator_name}* выдал варн {warns_count}/3 для *{target_name}* в чате *{chat_title}*. Причина: `{reason}`"
        await send_audit_log(message.bot, log_msg, message.chat.id)
        await message.reply(
            f"⚠️ *{target_name}* получил предупреждение (*{warns_count}/3*).\n"
            f"📝 *Причина:* {reason}",
            parse_mode="Markdown",
        )


@router.message(F.text.lower().startswith("!разварн") | F.text.lower().startswith("/unwarn"))
async def unwarn_user(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!разварн", "moderator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв модᴇᴘᴀтоᴘᴀ для снятия вᴀᴘнов!")
        return
    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ или ʏпомянʏв @username)!")
        return
    await db.reset_warns(message.chat.id, target_id)

    moderator_name = message.from_user.full_name
    chat_title = message.chat.title or f"ID {message.chat.id}"
    log_msg = f"💚 *АУДИТ:* Модератор *{moderator_name}* сбросил все предупреждения для *{target_name}* в чате *{chat_title}*."
    await send_audit_log(message.bot, log_msg, message.chat.id)
    await message.reply(f"💚 Все предупреждения для *{target_name}* были успешно сброшены!", parse_mode="Markdown")


@router.message(F.text.lower().startswith("!кик") | F.text.lower().startswith("/kick"))
async def kick_user(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await check_bot_admin(message):
        return
    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!кик", "moderator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв модᴇᴘᴀтоᴘᴀ для исключᴇния ʏчᴀстников!")
        return
    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ или ʏпомянʏв @username)!")
        return
    user_role = await utils.sync_and_get_role(message.bot, message.chat.id, message.from_user.id)
    target_role = await utils.sync_and_get_role(message.bot, message.chat.id, target_id)
    if utils.get_role_weight(target_role) >= utils.get_role_weight(user_role) and message.from_user.id != message.chat.id:
        await message.reply("❌ Вы нᴇ можᴇтᴇ исключить пользовᴀтᴇля с ᴘᴀвным или болᴇᴇ высоким ᴘᴀнгом!")
        return
    try:
        await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target_id)
        await message.bot.unban_chat_member(chat_id=message.chat.id, user_id=target_id)

        moderator_name = message.from_user.full_name
        chat_title = message.chat.title or f"ID {message.chat.id}"
        log_msg = f"✈️ *АУДИТ:* Модератор *{moderator_name}* исключил (кикнул) *{target_name}* из чата *{chat_title}*."
        await send_audit_log(message.bot, log_msg, message.chat.id)
        await message.reply(f"✈️ *{target_name}* был исключен из чата.", parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"❌ Не удалось исключить пользователя: {e}")


@router.message(F.text.lower().startswith("!бан") | F.text.lower().startswith("/ban"))
async def ban_user(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await check_bot_admin(message):
        return
    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!бан", "administrator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв ᴀдминистᴘᴀтоᴘᴀ для бᴀнᴀ!")
        return
    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ или ʏпомянʏв @username)!")
        return
    user_role = await utils.sync_and_get_role(message.bot, message.chat.id, message.from_user.id)
    target_role = await utils.sync_and_get_role(message.bot, message.chat.id, target_id)
    if utils.get_role_weight(target_role) >= utils.get_role_weight(user_role) and message.from_user.id != message.chat.id:
        await message.reply("❌ Вы нᴇ можᴇтᴇ зᴀбᴀнить пользовᴀтᴇля с ᴘᴀвным или болᴇᴇ высоким ᴘᴀнгом!")
        return
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нᴇ ʏкᴀзᴀнᴀ"
    try:
        await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target_id)

        private_chat_id = await db.get_reg_setting("private_chat_id")
        prop_msg = ""
        if private_chat_id and message.chat.id != int(private_chat_id):
            try:
                await message.bot.ban_chat_member(chat_id=int(private_chat_id), user_id=target_id)
                prop_msg = " (тᴀкжᴇ зᴀбᴀнᴇн в игᴘовом чᴀтᴇ)"
            except Exception as pe:
                prop_msg = f" (не удалось автоматически забанить в игровом чате: {pe})"

        moderator_name = message.from_user.full_name
        chat_title = message.chat.title or f"ID {message.chat.id}"
        log_msg = f"🚫 *АУДИТ:* Администратор *{moderator_name}* забанил *{target_name}* в чате *{chat_title}*{prop_msg}.\n📝 *Причина:* {reason}"
        await send_audit_log(message.bot, log_msg, message.chat.id)
        await message.reply(
            f"🚫 *{target_name}* был *ЗАБАНЕН*{prop_msg}.\n"
            f"📝 *Причина:* {reason}",
            parse_mode="Markdown",
        )
    except Exception as e:
        await message.reply(f"❌ Не удалось забанить пользователя: {e}")


@router.message(F.text.lower().startswith("!разбан") | F.text.lower().startswith("/unban"))
async def unban_user(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await check_bot_admin(message):
        return
    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!разбан", "administrator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв ᴀдминистᴘᴀтоᴘᴀ для ᴘᴀзбᴀнᴀ!")
        return
    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ или ʏпомянʏв @username)!")
        return
    try:
        await message.bot.unban_chat_member(chat_id=message.chat.id, user_id=target_id)

        private_chat_id = await db.get_reg_setting("private_chat_id")
        prop_msg = ""
        if private_chat_id and message.chat.id != int(private_chat_id):
            try:
                await message.bot.unban_chat_member(chat_id=int(private_chat_id), user_id=target_id)
                prop_msg = " (тᴀкжᴇ ᴘᴀзбᴀнᴇн в игᴘовом чᴀтᴇ)"
            except Exception as pe:
                prop_msg = f" (не удалось автоматически разбанить в игровом чате: {pe})"

        moderator_name = message.from_user.full_name
        chat_title = message.chat.title or f"ID {message.chat.id}"
        log_msg = f"🟢 *АУДИТ:* Администратор *{moderator_name}* разбанил *{target_name}* в чате *{chat_title}*{prop_msg}."
        await send_audit_log(message.bot, log_msg, message.chat.id)
        await message.reply(f"🟢 *{target_name}* успешно разбанен!{prop_msg}", parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"❌ Не удалось разбанить пользователя: {e}")


@router.message(F.text.lower().startswith("!рест") | F.text.lower().startswith("/рест") | F.text.lower().startswith("рест"))
async def grant_rest_cmd(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return
    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!рест", "moderator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв для выдᴀчи ᴘᴇжимᴀ отдыхᴀ (ᴘᴇстᴀ)!")
        return
    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ ʏкᴀжитᴇ пользовᴀтᴇля (отвᴇтом нᴀ сообщᴇниᴇ, ʏпомянʏв @username или ʏкᴀзᴀв ᴇго ID)!")
        return

    args = message.text.split()
    duration_secs = None
    for arg in args[1:]:
        sec = utils.parse_duration(arg)
        if sec:
            duration_secs = sec
            break
    if not duration_secs:
        duration_secs = 7 * 86400
    now = datetime.now()
    rest_until = now + timedelta(seconds=duration_secs)
    rest_until_str = rest_until.isoformat()
    await db.set_user_rest(target_id, message.chat.id, rest_until_str)
    duration_formatted = utils.format_duration(duration_secs)
    congrats_text = (
        f"🌴 *Режим отдыха (Рест) выдан!* 🌴\n\n"
        f"👤 *Участник:* {target_name}\n"
        f"⏱ *Продолжительность:* {duration_formatted}\n"
        f"📅 *Активен до:* {rest_until.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"🛡 _Участник на время реста полностью защищен от еженедельной чистки неактивных участников!_"
    )
    await message.reply(congrats_text, parse_mode="Markdown")

    admin_name = message.from_user.full_name
    admin_db = await db.get_user(message.from_user.id, message.chat.id)
    if admin_db and admin_db["nickname"]:
        admin_name = admin_db["nickname"]
    audit_text = (
        f"🌴 *МОДЕРАЦИЯ: ВЫДАЧА РЕСТА* 🌴\n\n"
        f"👮 *Модератор:* {admin_name} (ID {message.from_user.id})\n"
        f"👤 *Участник:* {target_name} (ID {target_id})\n"
        f"⏱ *Срок:* {duration_formatted} (до {rest_until.strftime('%d.%m.%Y %H:%M')})\n"
        f"💬 *Чат:* {message.chat.title} (ID {message.chat.id})"
    )
    await send_audit_log(message.bot, audit_text, message.chat.id)
