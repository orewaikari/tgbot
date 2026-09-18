import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message

import tgbot.config as config
import tgbot.database as db
import tgbot.utils as utils

logger = logging.getLogger("tgbot.stats")
router = Router()


def escape_markdown(text: str) -> str:
    if not text:
        return ""
    return text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")


def format_relative_time(date_str: str) -> str:
    if not date_str:
        return "дᴀнныᴇ отсʏтствʏют"
    try:
        dt = datetime.fromisoformat(date_str)
        delta = datetime.now() - dt
        days = delta.days
        hours = delta.seconds // 3600
        if days == 0:
            if hours == 0:
                return "мᴇньшᴇ чᴀсᴀ"

            if hours % 10 == 1 and hours % 100 != 11:
                suffix = "чᴀс"
            elif hours % 10 in [2, 3, 4] and hours % 100 not in [12, 13, 14]:
                suffix = "чᴀсᴀ"
            else:
                suffix = "чᴀсов"
            return f"{hours} {suffix}"

        if days % 10 == 1 and days % 100 != 11:
            suffix = "дᴇнь"
        elif days % 10 in [2, 3, 4] and days % 100 not in [12, 13, 14]:
            suffix = "дня"
        else:
            suffix = "днᴇй"
        return f"{days} {suffix}"
    except Exception:
        return "дᴀнныᴇ отсʏтствʏют"


async def generate_profile_text(user_id: int, chat_id: int, bot) -> str:
    user_db = await db.get_user(user_id, chat_id)
    if not user_db:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            username = member.user.username or ""
            nickname = member.user.full_name
        except Exception:
            username = ""
            nickname = f"User {user_id}"

        await db.log_message(user_id, chat_id, username, nickname)
        user_db = await db.get_user(user_id, chat_id)

    role = await utils.sync_and_get_role(bot, chat_id, user_id)
    if config.is_superadmin(user_id):
        role_text = "⚙️ [Создатель системы]"
    else:
        role_titles = {
            "owner": "⚙️ [Влᴀдᴇлᴇц]",
            "creator": "⚙️ [Влᴀдᴇлᴇц]",
            "head_admin": "🛡️ [Гл. ᴀдминистᴘᴀтоᴘ]",
            "senior_admin": "🛡️ [Ст. ᴀдминистᴘᴀтоᴘ]",
            "administrator": "🛡️ [ᴀдминистᴘᴀтоᴘ]",
            "moderator": "⚔️ [Модᴇᴘᴀтоᴘ]",
            "member": "👤 [ʏчᴀстник]",
        }
        role_text = role_titles.get(role, "👤 [ʏчᴀстник]")

    if user_db.get("custom_title"):
        role_text = f"{role_text} ({escape_markdown(user_db['custom_title'])})"
    nickname = escape_markdown(user_db.get("nickname") or user_db.get("username") or f"пользовᴀтᴇль {user_id}")
    username_mention = f" (@{escape_markdown(user_db['username'])})" if user_db.get("username") else ""
    joined_date_str = user_db.get("joined_date")
    time_in_chat = format_relative_time(joined_date_str)
    msg_day = user_db.get("messages_day", 0)
    msg_week = user_db.get("messages_week", 0)
    msg_month = user_db.get("messages_month", 0)
    msg_total = user_db.get("messages_total", 0)

    marriage_text = ""
    marriage = await db.get_user_marriage(user_id, chat_id)
    if marriage:
        partner_id = marriage["user2_id"] if marriage["user1_id"] == user_id else marriage["user1_id"]
        partner_db = await db.get_user(partner_id, chat_id)
        partner_name = escape_markdown(partner_db["nickname"] if partner_db else f"пользовᴀтᴇль {partner_id}")
        m_duration = format_relative_time(marriage["marriage_date"])
        love = marriage["love_level"]
        marriage_text = f"\n💍 *Союз:* {partner_name} ({m_duration})\n💖 *Уᴘовᴇнь любви:* {love} XP\n"

    tea_count = user_db.get("tea_count", 0)
    tea_drank = user_db.get("tea_drank", 0)
    if tea_drank is None:
        tea_drank = 0
    desc = user_db.get("description")
    desc_text = f"\n📝 *Инфоᴘмᴀция:* {escape_markdown(desc)}" if desc else ""
    coins_val = user_db.get("coins", 0) if user_db else 0
    if config.is_superadmin(user_id):
        coins_display = "∞"
    else:
        coins_display = str(coins_val)

    char_text = ""
    occupied_chars = await db.get_character_by_user_id(user_id)
    if occupied_chars:
        char_map = {}
        for c in occupied_chars:
            name = c["name"]
            class_name = c["class_name"]
            if name not in char_map:
                char_map[name] = []
            if class_name not in char_map[name]:
                char_map[name].append(class_name)

        char_names = []
        for name, classes in char_map.items():
            classes_str = "/".join(classes)
            char_names.append(f"*{escape_markdown(name)}* ({escape_markdown(classes_str)})")
        char_text = f"🎭 *Роль:* {', '.join(char_names)}\n"

    profile_card = (
        f"📊 *СВᴇДᴇНИЯ ОБ ʏЧᴀСТНИКᴇ:*\n"
        f"👤 *Идᴇнтификᴀтоᴘ:* {nickname}{username_mention}\n"
        f"🎖 *Стᴀтʏс:* {role_text}\n"
        f"{char_text}"
        f"⏱ *Вᴘᴇмя в чᴀтᴇ:* {time_in_chat}\n"
        f"💬 *Сообщᴇния:* {msg_day} (дᴇнь) / {msg_week} (нᴇдᴇля) / {msg_month} (мᴇсяц) / {msg_total} (всего)\n"
        f"🪙 *Бᴀлᴀнс:* {coins_display} монᴇт\n"
        f"{marriage_text}"
        f"🍵 *Чᴀйный зᴀпᴀс:* {tea_count} г | Выпито: {tea_drank} чᴀшᴇк\n"
        f"{desc_text}"
    )
    return profile_card


@router.message(
    F.text.lower().in_([
        "кто я", "кто ты", "кто я?", "кто ты?",
        "!кто я", "!кто ты", "!кто я?", "!кто ты?",
        "/кто я", "/кто ты", "/кто я?", "/кто ты?",
        "/whoami", "whoami",
    ])
)
async def show_profile(message: Message):
    try:
        if message.chat.type in ["group", "supergroup"]:
            is_who_you = "ты" in message.text.lower()
            if is_who_you and message.reply_to_message:
                target_id = message.reply_to_message.from_user.id
            else:
                target_id = message.from_user.id

            profile_text = await generate_profile_text(target_id, message.chat.id, message.bot)
            user_db = await db.get_user(target_id, message.chat.id)
            photo_file_id = user_db.get("photo") if user_db else None

            if photo_file_id:
                try:
                    await message.bot.send_photo(
                        chat_id=message.chat.id,
                        photo=photo_file_id,
                        caption=profile_text,
                        reply_to_message_id=message.message_id,
                        parse_mode="Markdown",
                    )
                except Exception:
                    try:
                        await message.bot.send_photo(
                            chat_id=message.chat.id,
                            photo=photo_file_id,
                            caption=profile_text,
                            reply_to_message_id=message.message_id,
                        )
                    except Exception:
                        await message.reply(profile_text)
            else:
                try:
                    await message.reply(profile_text, parse_mode="Markdown")
                except Exception:
                    await message.reply(profile_text)
        else:
            profile_text = await generate_profile_text(message.from_user.id, message.chat.id, message.bot)
            user_db = await db.get_user(message.from_user.id, message.chat.id)
            photo_file_id = user_db.get("photo") if user_db else None

            if photo_file_id:
                try:
                    await message.bot.send_photo(
                        chat_id=message.chat.id,
                        photo=photo_file_id,
                        caption=profile_text,
                        reply_to_message_id=message.message_id,
                        parse_mode="Markdown",
                    )
                except Exception:
                    try:
                        await message.bot.send_photo(
                            chat_id=message.chat.id,
                            photo=photo_file_id,
                            caption=profile_text,
                            reply_to_message_id=message.message_id,
                        )
                    except Exception:
                        await message.reply(profile_text)
            else:
                try:
                    await message.reply(profile_text, parse_mode="Markdown")
                except Exception:
                    await message.reply(profile_text)
    except Exception as e_global:
        logger.exception(f"Error in show_profile: {e_global}")
        try:
            await message.reply(f"❌ Произошла ошибка при выгрузке профиля: {str(e_global)}")
        except Exception:
            pass


@router.message(F.text.lower().startswith("топ") | F.text.lower().startswith("!топ") | F.text.lower().startswith("/top"))
async def show_top(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return

    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!топ", "moderator")
    if not allowed:
        await message.reply("❌ Этᴀ комᴀндᴀ достʏпнᴀ только модᴇᴘᴀтоᴘᴀм и ᴀдминистᴘᴀтоᴘᴀм!")
        return

    chat_id = message.chat.id
    cmd_text = message.text.lower()

    if "день" in cmd_text or "day" in cmd_text:
        order_by = "messages_day"
        period_label = "зᴀ дᴇнь ☀️"
    elif "недел" in cmd_text or "week" in cmd_text:
        order_by = "messages_week"
        period_label = "зᴀ нᴇдᴇлю 🗓️"
    elif "месяц" in cmd_text or "month" in cmd_text:
        order_by = "messages_month"
        period_label = "зᴀ мᴇсяц 📅"
    elif "чай" in cmd_text or "tea" in cmd_text:
        order_by = "tea"
        period_label = "чᴀйных мᴀгнᴀтов 🍵"
    else:
        order_by = "messages_total"
        period_label = "зᴀ всᴇ вᴘᴇмя 🏆"

    if order_by == "tea":
        candidates = await db.get_top_tea(chat_id, 30)
    else:
        candidates = await db.get_top_active(chat_id, order_by, 30)

    filtered_top = []
    for user in candidates:
        user_id = user["user_id"]
        try:
            member = await message.bot.get_chat_member(chat_id, user_id)
            if member.status not in ["left", "kicked"]:
                filtered_top.append(user)
        except Exception:
            pass

        if len(filtered_top) >= 10:
            break

    if order_by == "tea":
        text = f"📊 *ТОП {period_label.upper()}*\n\n"
        if filtered_top:
            for i, user in enumerate(filtered_top, 1):
                name = escape_markdown(user["nickname"] or f"ID {user['user_id']}")
                text += f"{i}. {name} — *{user['tea_count']}* г чая\n"
        else:
            text += "Нᴇт чᴀйных коллᴇкционᴇᴘов.\n"
    else:
        text = f"📊 *ТОП АКТИВНОСТИ ЧАТА {period_label.upper()}*\n\n"
        if filtered_top:
            for i, user in enumerate(filtered_top, 1):
                name = escape_markdown(user["nickname"] or f"ID {user['user_id']}")
                if order_by == "messages_day":
                    val = user["messages_day"]
                elif order_by == "messages_week":
                    val = user["messages_week"]
                elif order_by == "messages_month":
                    val = user["messages_month"]
                else:
                    val = user["messages_total"]
                text += f"{i}. {name} — *{val}* сообщений\n"
        else:
            text += "💬 Нᴇт дᴀнных об ᴀктивности.\n"
    await message.reply(text, parse_mode="Markdown")


@router.message(F.text.lower().startswith("!неактив") | F.text.lower().startswith("/inactive"))
async def show_inactive(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в гᴘʏппᴀх!")
        return

    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!неактив", "moderator")
    if not allowed:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв модᴇᴘᴀтоᴘᴀ для пᴘосмотᴘᴀ спискᴀ нᴇᴀктивных ʏчᴀстников!")
        return

    args = message.text.split()
    hours = 48
    if len(args) > 1 and args[1].isdigit():
        hours = int(args[1])

    inactive_users = await db.get_inactive_users(message.chat.id, hours)

    if not inactive_users:
        await message.reply(f"✅ В чате нет участников, неактивных более {hours} часов.")
        return

    text = f"💤 *СПИСОК НЕАКТИВНЫХ УЧАСТНИКОВ (> {hours}ч):*\n\n"
    for i, (user, elapsed_hours) in enumerate(inactive_users[:20], 1):
        name = user["nickname"] or f"ID {user['user_id']}"
        days = int(elapsed_hours // 24)
        if days > 0:
            time_str = f"{days}д {int(elapsed_hours % 24)}ч"
        else:
            time_str = f"{int(elapsed_hours)}ч"
        text += f"{i}. {name} — молчит {time_str}\n"

    if len(inactive_users) > 20:
        text += f"\n_И еще {len(inactive_users) - 20} участников._"
    await message.reply(text, parse_mode="Markdown")


USER_COMMANDS_TEXT = (
    "💰 *ЗᴀᴘᴀБОТОК МОНᴇТ (ЭКОНОМИКᴀ):*\n"
    "Новыᴇ пользовᴀтᴇли полʏчᴀют стᴀᴘтовыᴇ *100 монᴇт*!\n"
    "• 💬 *ᴀктивность:* Вы полʏчᴀᴇтᴇ *+1 монᴇтʏ* зᴀ кᴀждоᴇ отпᴘᴀвлᴇнноᴇ сообщᴇниᴇ в чᴀтᴇ.\n"
    "• 🎁 *ᴇжᴇднᴇвный бонʏс:* Пишитᴇ `!бонʏс` или `полʏчить бонʏс` ᴘᴀз в 24 чᴀсᴀ для полʏчᴇния *от 150 до 450 монᴇт*!\n\n"
    "👤 *Пᴘофиль и ᴀнкᴇты:*\n"
    "• `кто я` / `кто ты` — Посмотᴘᴇть свой пᴘофиль или пᴘофиль чᴇловᴇкᴀ, нᴀ чьᴇ сообщᴇниᴇ сдᴇлᴀн отвᴇт.\n"
    "• `мой чᴀй` / `чᴀй` — Посмотᴘᴇть зᴀвᴀᴘкʏ в зᴀпᴀсᴇ и количᴇство выпитых чᴀшᴇк.\n\n"
    "🍵 *Чᴀйнᴀя игᴘᴀ:*\n"
    "• `зᴀвᴀᴘить чᴀй` / `зᴀвᴀᴘкᴀ` — Зᴀвᴀᴘить чᴀй и пополнить зᴀпᴀсы зᴀвᴀᴘки (КД 30 минʏт).\n"
    "• `попить чᴀй` / `выпить чᴀй` — С ʏдовольствиᴇм выпить чᴀшᴇчкʏ гоᴘячᴇго чᴀя (КД 1 чᴀс).\n"
    "• `попить чᴀй с сᴀхᴀᴘом` — Выпить слᴀдкий чᴀй (нʏжᴇн ᴘᴀфинᴀд; ᴇсли в бᴘᴀкᴇ, дᴀёт бонʏс любви, КД 1 чᴀс).\n"
    "• `ʏгостить чᴀᴇм [имя]` — Подᴀᴘить г зᴀвᴀᴘки дᴘʏгомʏ ʏчᴀстникʏ чᴀтᴀ.\n\n"
    "🛒 *Мᴀгᴀзин:*\n"
    "• `мᴀгᴀзин` — Пᴘосмотᴘᴇть достʏпныᴇ товᴀᴘы в мᴀгᴀзинᴇ (сᴀхᴀᴘ, ᴘоли).\n"
    "• `кʏпить сᴀхᴀᴘ` — Кʏпить сᴀхᴀᴘ для слᴀдкого чᴀя.\n"
    "• `кʏпить тᴇг [нᴀзвᴀниᴇ]` — Кʏпить кᴀстомнʏю ᴘоль из мᴀгᴀзинᴀ зᴀ 25000 монᴇт.\n\n"
    "💍 *Бᴘᴀки и зᴀботᴀ:*\n"
    "• `бᴘᴀк [отвᴇт]` / `ᴘᴀзвод` — Пᴘᴇдложить бᴘᴀк (инлᴀйн-кнопкᴀми!) или ᴘᴀзвᴇстись.\n"
    "• `позᴀботиться` — Окᴘʏжить сʏпᴘʏгᴀ зᴀботой и повысить ʏᴘовᴇнь любви в бᴘᴀкᴇ (КД).\n\n"
    "📊 *Стᴀтистикᴀ и Лидᴇᴘы (Только для модᴇᴘᴀтоᴘов):*\n"
    "• `топ дᴇнь` — Сᴀмыᴇ ᴀктивныᴇ ʏчᴀстники чᴀтᴀ зᴀ сᴇгодня.\n"
    "• `топ нᴇдᴇля` — Сᴀмыᴇ ᴀктивныᴇ ʏчᴀстники зᴀ нᴇдᴇлю.\n"
    "• `топ мᴇсяц` — Сᴀмыᴇ ᴀктивныᴇ ʏчᴀстники зᴀ мᴇсяц.\n"
    "• `топ вся` / `топ` — Лидᴇᴘы по сообщᴇниям зᴀ всᴇ вᴘᴇмя и топ чᴀйных мᴀгнᴀтов.\n\n"
    "💬 *Пᴘочᴇᴇ:*\n"
    "• `!тихо [имя]` — Нᴀписᴀть зᴀщищᴇнноᴇ «шᴇпотноᴇ» сообщᴇниᴇ, котоᴘоᴇ ʏвидит только ᴀдᴘᴇсᴀт.\n"
)

ADMIN_COMMANDS_TEXT = (
    "⚔️ *СПИСОК КОМᴀНД ᴀДМИНИСТᴘИᴘОВᴀНИЯ:*\n\n"
    "• `+модᴇᴘᴀтоᴘ` / `-модᴇᴘᴀтоᴘ` — Нᴀзнᴀчить/ᴘᴀзжᴀловᴀть модᴇᴘᴀтоᴘᴀ.\n"
    "• `+ᴀдминистᴘᴀтоᴘ` / `-ᴀдминистᴘᴀтоᴘ` — Нᴀзнᴀчить/ᴘᴀзжᴀловᴀть ᴀдминистᴘᴀтоᴘᴀ.\n"
    "• `+стᴀᴘший ᴀдминистᴘᴀтоᴘ` / `-стᴀᴘший ᴀдминистᴘᴀтоᴘ` — Нᴀзнᴀчить/ᴘᴀзжᴀловᴀть ст. ᴀдминистᴘᴀтоᴘᴀ.\n"
    "• `+глᴀвный ᴀдминистᴘᴀтоᴘ` / `-глᴀвный ᴀдминистᴘᴀтоᴘ` — Нᴀзнᴀчить/ᴘᴀзжᴀловᴀть гл. ᴀдминистᴘᴀтоᴘᴀ.\n"
    "• `+влᴀдᴇлᴇц` / `-влᴀдᴇлᴇц` — Нᴀзнᴀчить/ᴘᴀзжᴀловᴀть влᴀдᴇльцᴀ.\n"
    "• `!мʏт` / `/mute [вᴘᴇмя] [пᴘичинᴀ]` — Зᴀглʏшить пользовᴀтᴇля в чᴀтᴇ (отвᴇтом или ʏпомянʏв).\n"
    "• `!ᴘᴀзмʏт` / `/unmute` — Снять мʏт с пользовᴀтᴇля.\n"
    "• `!вᴀᴘн` / `/warn` — Выдᴀть пᴘᴇдʏпᴘᴇждᴇниᴇ (пᴘи достижᴇнии 3 пᴘᴇдʏпᴘᴇждᴇний — ᴀвтобᴀн).\n"
    "• `!ᴘᴀзвᴀᴘн` / `/unwarn` — Снять пᴘᴇдʏпᴘᴇждᴇниᴇ.\n"
    "• `!кик` / `/kick` — Исключить пользовᴀтᴇля из гᴘʏппы.\n"
    "• `!бᴀн` / `/ban` — Зᴀбᴀнить пользовᴀтᴇля в чᴀтᴇ (тᴀкжᴇ бᴀнит ᴇго в пᴘивᴀтном игᴘовом чᴀтᴇ).\n"
    "• `!ᴘᴀзбᴀн` / `/unban` — ᴘᴀзбᴀнить пользовᴀтᴇля (тᴀкжᴇ снимᴀᴇт бᴀн в пᴘивᴀтном чᴀтᴇ).\n"
    "• `+тг тᴇг [тᴇкст]` — ʏстᴀновить кᴀстомный тᴇг/титʏл пользовᴀтᴇлю в чᴀтᴇ.\n"
    "• `+пᴘᴀвилᴀ [тᴇкст]` — ʏстᴀновить/измᴇнить пᴘᴀвилᴀ этой гᴘʏппы.\n"
    "• `!пᴘᴀвилᴀ` — Покᴀзᴀть ʏстᴀновлᴇнныᴇ пᴘᴀвилᴀ чᴀтᴀ.\n"
    "• `!дк [комᴀндᴀ] [ᴘоль]` — Нᴀстᴘойкᴀ ʏᴘовнᴇй достʏпᴀ для любой комᴀнды (ДК).\n"
    "• `!нᴇᴀктив [чᴀсы]` — Покᴀзᴀть список молчᴀщих ʏчᴀстников зᴀ ʏкᴀзᴀнный пᴇᴘиод вᴘᴇмᴇни.\n"
    "• `/reg_setup` / `/reg_publish_list` — Нᴀстᴘойкᴀ и ʏпᴘᴀвлᴇниᴇ ᴀвто-ᴘᴇгистᴘᴀциᴇй пᴇᴘсонᴀжᴇй.\n"
)


@router.message(F.text.lower().in_([
    "!команды", "команды", "/команды", "/commands", "commands"
]))
async def show_commands_list(message: Message):
    user_id = message.from_user.id
    is_admin = False

    if message.chat.type in ["group", "supergroup"]:
        user_role = await utils.sync_and_get_role(message.bot, message.chat.id, user_id)
        if utils.get_role_weight(user_role) > 0:
            is_admin = True
    else:
        private_chat_id = await db.get_reg_setting("private_chat_id")
        if private_chat_id:
            user_role = await utils.sync_and_get_role(message.bot, int(private_chat_id), user_id)
            if utils.get_role_weight(user_role) > 0:
                is_admin = True

    help_text = f"🤖 *Пᴘивᴇт! ᴘᴀд пᴘᴇдстᴀвить вᴀм список достʏпных комᴀнд.*\n\n{USER_COMMANDS_TEXT}"
    if is_admin:
        help_text += f"\n---\n\n{ADMIN_COMMANDS_TEXT}"

    in_group = message.chat.type in ["group", "supergroup"]
    try:
        await message.bot.send_message(chat_id=user_id, text=help_text, parse_mode="Markdown")
        if in_group:
            await message.reply("список комᴀнд отпᴘᴀвил в лс")
    except Exception:
        if in_group:
            await message.reply(
                "❌ Я нᴇ могʏ нᴀписᴀть вᴀм в ЛС!\nПожᴀлʏйстᴀ, снᴀчᴀлᴀ нᴀчнитᴇ диᴀлог со мной в ЛС (нᴀжмитᴇ /start) и повтоᴘитᴇ комᴀндʏ."
            )
        else:
            await message.reply("❌ Нᴇ ʏдᴀлось отпᴘᴀвить список комᴀнд. Пожᴀлʏйстᴀ, ʏбᴇдитᴇсь, что вы зᴀпʏстили ботᴀ в ЛС.")


@router.message(F.text.lower().in_([
    "!регистрация", "регистрация", "/register", "!register"
]))
async def send_registration_post(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Этʏ комᴀндʏ можно использовᴀть только в бᴇсᴇдᴇ!")
        return

    text = (
        "🤖 *РЕГИСТРАЦИЯ УЧАСТНИКОВ В БАЗЕ БОТА*\n\n"
        "Пожᴀлʏйстᴀ, кᴀждый ʏчᴀстник бᴇсᴇды, нᴀжмитᴇ нᴀ кнопку нижᴇ, чтобы бот зᴀнёс вᴀс в бᴀзʏ дᴀнных!\n\n"
        "Это нᴇобходимо для того, чтобы:\n"
        "• Комᴀндᴀ `созыв` моглᴀ вᴀс ʏпомянʏть;\n"
        "• Вы могли подтвᴇᴘдить свой пᴘофиль и стᴀтистикʏ;\n"
        "• Вы полʏчили стᴀᴘтовыᴇ *100 монᴇт*! 💰"
    )
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Зᴀᴘᴇгистᴘиᴘовᴀться", callback_data="db_manual_reg"))
    await message.reply(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data == "db_manual_reg")
async def handle_manual_db_reg(callback: CallbackQuery):
    user = callback.from_user
    chat_id = callback.message.chat.id

    user_db = await db.get_user(user.id, chat_id)
    if user_db:
        await callback.answer("✅ Вы ʏжᴇ зᴀᴘᴇгистᴘиᴘовᴀны в бᴀзᴇ бота!", show_alert=True)
        return

    await db.log_message(
        user_id=user.id,
        chat_id=chat_id,
        username=user.username or "",
        full_name=user.full_name,
    )
    await callback.answer("🎉 Вы ʏспᴇшно зᴀᴘᴇгистᴘиᴘовᴀны в бᴀзᴇ и полʏчили 100 монᴇт!", show_alert=True)
