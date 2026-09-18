import json
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ChatJoinRequest, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import tgbot.database as db
import tgbot.utils as utils


class ProfileEditStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_description = State()
    waiting_for_photo = State()


class AnonAppealStates(StatesGroup):
    waiting_for_appeal_message = State()


logger = logging.getLogger("tgbot.registration")
router = Router()
_sent_applications = set()


def escape_markdown(text: str) -> str:
    if not text:
        return ""
    return text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")


async def check_reg_admin(message: Message) -> bool:
    is_admin = await utils.check_permission(
        message.bot, message.chat.id, message.from_user.id, "reg_admin", "administrator"
    )
    if not is_admin:
        await message.reply("❌ ʏ вᴀс нᴇт пᴘᴀв ᴀдминистᴘᴀтоᴘᴀ для выполнᴇния этой комᴀнды!")
        return False
    return True


async def show_member_profile(message_or_callback, user_id: int, chat_id: int, bot: Bot):
    from tgbot.handlers.stats import generate_profile_text

    profile_text = await generate_profile_text(user_id, chat_id, bot)
    user_db = await db.get_user(user_id, chat_id)
    photo_file_id = user_db.get("photo") if user_db else None

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Измᴇнить имя", callback_data="prof_edit_name"),
        InlineKeyboardButton(text="✏️ Измᴇнить описᴀниᴇ", callback_data="prof_edit_desc"),
    )
    builder.row(
        InlineKeyboardButton(text="📸 Измᴇнить фото", callback_data="prof_edit_photo"),
        InlineKeyboardButton(text="🔄 Обновить ᴀнкᴇтʏ", callback_data="prof_refresh"),
    )

    markup = builder.as_markup()
    is_callback = isinstance(message_or_callback, CallbackQuery)
    target = message_or_callback.message if is_callback else message_or_callback

    if photo_file_id:
        if is_callback:
            try:
                await target.delete()
            except Exception:
                pass
        await bot.send_photo(
            chat_id=user_id,
            photo=photo_file_id,
            caption=profile_text,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    else:
        if is_callback:
            try:
                await target.edit_text(text=profile_text, reply_markup=markup, parse_mode="Markdown")
            except Exception:
                try:
                    await bot.send_message(chat_id=user_id, text=profile_text, reply_markup=markup, parse_mode="Markdown")
                except Exception:
                    pass
        else:
            await bot.send_message(chat_id=user_id, text=profile_text, reply_markup=markup, parse_mode="Markdown")


@router.callback_query(F.data == "prof_edit_name")
async def profile_edit_name_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply("📝 Пожᴀлʏйстᴀ, ввᴇдитᴇ вᴀшᴇ новоᴇ имя/никнᴇйм для ᴀнкᴇты (нᴇ болᴇᴇ 32 символов):")
    await state.set_state(ProfileEditStates.waiting_for_nickname)
    await callback.answer()


@router.callback_query(F.data == "prof_edit_desc")
async def profile_edit_desc_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply("📝 Пожᴀлʏйстᴀ, ввᴇдитᴇ описᴀниᴇ для вᴀшᴇй ᴀнкᴇты (ᴘᴀсскᴀжитᴇ о сᴇбᴇ, своих интᴇᴘᴇсᴀх и т.д., нᴇ болᴇᴇ 150 символов):")
    await state.set_state(ProfileEditStates.waiting_for_description)
    await callback.answer()


@router.callback_query(F.data == "prof_edit_photo")
async def profile_edit_photo_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply("📸 Пожᴀлʏйстᴀ, отпᴘᴀвьтᴇ фотогᴘᴀфию/кᴀᴘтинкʏ, котоᴘʏю вы хотитᴇ пᴘикᴘᴇпить к своᴇй ᴀнкᴇтᴇ:")
    await state.set_state(ProfileEditStates.waiting_for_photo)
    await callback.answer()


@router.callback_query(F.data == "prof_refresh")
async def profile_refresh_callback(callback: CallbackQuery, bot: Bot):
    private_chat_id = await db.get_reg_setting("private_chat_id")
    if private_chat_id:
        await show_member_profile(callback, callback.from_user.id, int(private_chat_id), bot)
    else:
        await callback.answer("⚠️ Ошибкᴀ: ID чᴀтᴀ нᴇ нᴀстᴘоᴇн!", show_alert=True)


@router.message(ProfileEditStates.waiting_for_nickname, F.chat.type == "private")
async def save_profile_nickname(message: Message, state: FSMContext, bot: Bot):
    nickname = message.text.strip() if message.text else ""
    if not nickname or len(nickname) > 32:
        await message.reply("❌ Нᴇвᴇᴘный фоᴘмᴀт! Никнᴇйм должᴇн быть тᴇкстовым и содᴇᴘжᴀть нᴇ болᴇᴇ 32 символов. Попᴘобʏйтᴇ ᴇщᴇ ᴘᴀз:")
        return

    private_chat_id = await db.get_reg_setting("private_chat_id")
    if private_chat_id:
        await db.update_user_nickname(message.from_user.id, int(private_chat_id), nickname)
    await state.clear()
    await show_member_profile(message, message.from_user.id, int(private_chat_id) if private_chat_id else 0, bot)


@router.message(ProfileEditStates.waiting_for_description, F.chat.type == "private")
async def save_profile_description(message: Message, state: FSMContext, bot: Bot):
    desc = message.text.strip() if message.text else ""
    if not desc or len(desc) > 150:
        await message.reply("❌ Нᴇвᴇᴘный фоᴘмᴀт! Описᴀниᴇ должно содᴇᴘжᴀть нᴇ болᴇᴇ 150 символов. Попᴘобʏйтᴇ ᴇщᴇ ᴘᴀз:")
        return

    private_chat_id = await db.get_reg_setting("private_chat_id")
    if private_chat_id:
        await db.update_user_description(message.from_user.id, int(private_chat_id), desc)
    await state.clear()
    await show_member_profile(message, message.from_user.id, int(private_chat_id) if private_chat_id else 0, bot)


@router.message(ProfileEditStates.waiting_for_photo, F.chat.type == "private")
async def save_profile_photo(message: Message, state: FSMContext, bot: Bot):
    if not message.photo:
        await message.reply("❌ Пожᴀлʏйстᴀ, отпᴘᴀвьтᴇ имᴇнно фотогᴘᴀфию/кᴀᴘтинкʏ! Попᴘобʏйтᴇ ᴇщᴇ ᴘᴀз:")
        return

    photo_file_id = message.photo[-1].file_id
    private_chat_id = await db.get_reg_setting("private_chat_id")
    if private_chat_id:
        await db.update_user_photo(message.from_user.id, int(private_chat_id), photo_file_id)
    await state.clear()
    await show_member_profile(message, message.from_user.id, int(private_chat_id) if private_chat_id else 0, bot)


@router.message(F.chat.type == "private", F.text.lower() == "/start")
async def start_menu_cmd(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    is_rejected = await db.is_user_rejected(message.from_user.id)
    private_chat_id = await db.get_reg_setting("private_chat_id")
    is_banned = False
    is_member = False

    if private_chat_id:
        try:
            member = await bot.get_chat_member(chat_id=int(private_chat_id), user_id=message.from_user.id)
            if member.status == "kicked":
                is_banned = True
            elif member.status in ["member", "administrator", "creator", "owner"]:
                is_member = True
        except Exception:
            pass

    if is_rejected or is_banned:
        block_text = (
            "❌ *Доступ заблокирован.*\n\n"
            "Вам отказано в принятии во флуд или вы были забанены.\n"
            "По всем вопросам обращайтесь к кураторам проекта: @neoghoul или @jjurny."
        )
        await message.reply(block_text, parse_mode="Markdown")
        return

    greeting_text = (
        "👋 *Приветствуем вас в нашем боте!*\n\n"
        "Пожалуйста, выберите необходимое действие ниже:"
    )
    builder = InlineKeyboardBuilder()
    if is_member:
        builder.row(
            InlineKeyboardButton(text="📝 Изменить анкету", callback_data="start_join_flood"),
            InlineKeyboardButton(text="🔹 Анонимное обращение", callback_data="start_anon_appeal"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🔹 Вступить во флуд", callback_data="start_join_flood"),
            InlineKeyboardButton(text="🔹 Анонимное обращение", callback_data="start_anon_appeal"),
        )
    await message.reply(greeting_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data == "start_join_flood")
async def handle_start_join_flood(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()

    user_id = callback.from_user.id
    private_chat_id = await db.get_reg_setting("private_chat_id")
    is_member = False
    if private_chat_id:
        try:
            member = await bot.get_chat_member(chat_id=int(private_chat_id), user_id=user_id)
            if member.status in ["member", "administrator", "creator", "owner"]:
                is_member = True
        except Exception as e:
            logger.warning(f"Failed to check group membership for {user_id}: {e}")

    if is_member:
        await show_member_profile(callback.message, user_id, int(private_chat_id), bot)
        return

    info_channel_url = await db.get_reg_setting("info_channel_url", "https://t.me/your_channel")
    rules_teletype_url = await db.get_reg_setting("rules_teletype_url", "https://teletype.in/@rules")
    greeting_text = (
        "👋 *Для вступления во флуд необходимо ознакомиться с нашими правилами.*\n\n"
        "Пожалуйста, обязательно ознакомьтесь с ресурсами:\n"
        f"📢 [Информационный канал]({info_channel_url})\n"
        f"📖 [Правила проекта на Teletype]({rules_teletype_url})\n\n"
        "После ознакомления нажмите на кнопку ниже, чтобы начать регистрацию персонажа."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔹 Ознакомился", callback_data="reg_rules_agreed"))
    builder.row(InlineKeyboardButton(text="🔹 Назад", callback_data="start_back_to_menu"))

    await callback.message.edit_text(
        greeting_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "start_anon_appeal")
async def handle_start_anon_appeal(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await state.set_state(AnonAppealStates.waiting_for_appeal_message)
    appeal_prompt = (
        "📝 *Анонимное обращение к администрации.*\n\n"
        "Вы вошли в режим обращения. Все сообщения, которые вы отправляете сюда, анонимно передаются администрации.\n\n"
        "Вы можете вести непрерывный диалог. Как только вы захотите закончить, нажмите на кнопку ниже, чтобы выйти."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚪 Выйти в главное меню", callback_data="start_back_to_menu"))
    await callback.message.edit_text(appeal_prompt, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data == "start_back_to_menu")
async def handle_back_to_menu(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await state.clear()

    private_chat_id = await db.get_reg_setting("private_chat_id")
    is_member = False
    if private_chat_id:
        try:
            member = await bot.get_chat_member(chat_id=int(private_chat_id), user_id=callback.from_user.id)
            if member.status in ["member", "administrator", "creator", "owner"]:
                is_member = True
        except Exception:
            pass

    greeting_text = (
        "👋 *Приветствуем вас в нашем боте!*\n\n"
        "Пожалуйста, выберите необходимое действие ниже:"
    )
    builder = InlineKeyboardBuilder()
    if is_member:
        builder.row(
            InlineKeyboardButton(text="📝 Изменить анкету", callback_data="start_join_flood"),
            InlineKeyboardButton(text="🔹 Анонимное обращение", callback_data="start_anon_appeal"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🔹 Вступить во флуд", callback_data="start_join_flood"),
            InlineKeyboardButton(text="🔹 Анонимное обращение", callback_data="start_anon_appeal"),
        )
    await callback.message.edit_text(greeting_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.message(AnonAppealStates.waiting_for_appeal_message)
async def process_anon_appeal_message(message: Message, state: FSMContext, bot: Bot):
    admin_chat_id = await db.get_reg_setting("admin_chat_id")
    if not admin_chat_id:
        await message.reply("❌ Ошибка: чат администрации не настроен. Попробуйте позже.")
        await state.clear()
        return
    try:
        await bot.send_message(
            chat_id=int(admin_chat_id),
            text="📩 *Получено новое анонимное обращение:*",
            parse_mode="Markdown",
            message_thread_id=101,
        )
        copied_msg = await message.copy_to(chat_id=int(admin_chat_id), message_thread_id=101)
        await db.save_anonymous_appeal(copied_msg.message_id, message.from_user.id)

        response_text = (
            "✅ *Ваше сообщение доставлено администрации.*\n\n"
            "Вы можете продолжать отправлять сюда сообщения для продолжения диалога, либо выйти обратно в меню."
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🚪 Выйти в главное меню", callback_data="start_back_to_menu"))
        await message.reply(response_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to forward anonymous appeal: {e}")
        await message.reply("❌ Произошла ошибка при отправке обращения. Пожалуйста, попробуйте еще раз.")


@router.callback_query(F.data == "reg_rules_agreed")
async def show_classes(callback: CallbackQuery):
    text = (
        "🎭 *Выбоᴘ клᴀссᴀ*\n\n"
        "Пожᴀлʏйстᴀ, выбᴇᴘитᴇ клᴀсс пᴇᴘсонᴀжᴇй, чтобы пᴘосмотᴘᴇть достʏпных гᴇᴘоᴇв:"
    )
    builder = InlineKeyboardBuilder()
    classes = ["Ассасин", "Боец", "Маг", "Стрелок", "Танк", "Поддержка"]
    for cls in classes:
        builder.add(InlineKeyboardButton(text=f"🔹 {cls}", callback_data=f"reg_class:{cls}"))
    builder.adjust(2)
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "reg_back_to_classes")
async def process_back_to_classes(callback: CallbackQuery):
    await show_classes(callback)


@router.callback_query(F.data.startswith("reg_class:"))
async def show_characters(callback: CallbackQuery):
    parts = callback.data.split(":")
    class_name = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    characters = await db.get_characters_by_class(class_name)
    PAGE_SIZE = 14
    total_characters = len(characters)
    total_pages = (total_characters + PAGE_SIZE - 1) // PAGE_SIZE
    if page < 0:
        page = 0
    elif page >= total_pages and total_pages > 0:
        page = total_pages - 1
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_chars = characters[start_idx:end_idx]

    text = (
        f"🎭 *Класс: {class_name}* (страница {page + 1}/{total_pages if total_pages > 0 else 1})\n\n"
        "Нижᴇ пᴘᴇдстᴀвлᴇн список пᴇᴘсонᴀжᴇй. Выбᴇᴘитᴇ свободного (с гᴀлочкой ✅), "
        "чтобы зᴀнять ᴇго и подᴀть зᴀявкʏ нᴀ встʏплᴇниᴇ в бᴇсᴇдʏ:\n\n"
        "🟢 ✅ — Свободᴇн\n"
        "🔴 ❌ — Зᴀнят игᴘоком\n"
        "👑 👑 — Зᴀнят ᴀдминистᴘᴀциᴇй\n"
        "🔵 🛡️ — Зᴀбᴘониᴘовᴀн"
    )
    builder = InlineKeyboardBuilder()
    for char in page_chars:
        status_icon = "✅"
        if char["status"] == "occupied":
            status_icon = "❌"
        elif char["status"] == "occupied_admin":
            status_icon = "👑"
        elif char["status"] == "reserved":
            status_icon = "🛡️"

        builder.add(InlineKeyboardButton(
            text=f"{status_icon} {char['name']}",
            callback_data=f"reg_char:{char['name']}:{page}",
        ))
    builder.adjust(2)

    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"reg_class:{class_name}:{page - 1}"))
        else:
            nav_buttons.append(InlineKeyboardButton(text="⏹️", callback_data="ignore_nav"))
        nav_buttons.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="ignore_nav"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Далее ➡️", callback_data=f"reg_class:{class_name}:{page + 1}"))
        else:
            nav_buttons.append(InlineKeyboardButton(text="⏹️", callback_data="ignore_nav"))
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="🔹 Нᴀзᴀд к клᴀссᴀм", callback_data="reg_back_to_classes"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "ignore_nav")
async def handle_ignore_nav(callback: CallbackQuery):
    await callback.answer()


async def send_application_to_admins(
    bot: Bot, user_id: int, username: str, nickname: str, char_name: str, class_name: str
) -> bool:
    admin_chat_id = await db.get_reg_setting("admin_chat_id")
    if not admin_chat_id:
        logger.error("Admin chat ID is not configured!")
        return False

    photo_file_id = None
    try:
        photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
        if photos and photos.photos:
            photo_file_id = photos.photos[0][-1].file_id
    except Exception as e:
        logger.warning(f"Failed to fetch profile photos for user {user_id}: {e}")

    esc_nickname = escape_markdown(nickname)
    esc_username = escape_markdown(username)
    esc_char_name = escape_markdown(char_name)
    esc_class_name = escape_markdown(class_name)
    caption = (
        "📥 *Новᴀя зᴀявкᴀ нᴀ ᴘоль!*\n\n"
        f"👤 *Никнейм:* {esc_nickname}\n"
        f"🏷️ *Юзернейм:* {esc_username}\n"
        f"🆔 *TG ID:* `{user_id}`\n"
        f"🎭 *Выбранный персонаж:* *{esc_char_name}* ({esc_class_name})\n\n"
        "Пожᴀлʏйстᴀ, пᴘимитᴇ или отклонитᴇ зᴀявкʏ:"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔹 Пᴘинять", callback_data=f"adm_appr:{user_id}:{char_name}"),
        InlineKeyboardButton(text="🔹 Отклонить", callback_data=f"adm_decl:{user_id}:{char_name}"),
    )
    try:
        if photo_file_id:
            await bot.send_photo(
                chat_id=int(admin_chat_id),
                photo=photo_file_id,
                caption=caption,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown",
                message_thread_id=103,
            )
        else:
            await bot.send_message(
                chat_id=int(admin_chat_id),
                text=caption,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown",
                message_thread_id=103,
            )
        return True
    except Exception as e:
        logger.error(f"Failed to send request to admin chat: {e}")
        return False


@router.callback_query(F.data.startswith("reg_char:"))
async def select_character(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    char_name = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    char = await db.get_character_by_name(char_name)
    if not char:
        await callback.answer("⚠️ Пᴇᴘсонᴀж нᴇ нᴀйдᴇн!", show_alert=True)
        return
    user_id = callback.from_user.id

    if user_id not in [5026834657, 8002165201]:
        occupied_chars = await db.get_character_by_user_id(user_id)
        if occupied_chars:
            already_char = occupied_chars[0]["name"]
            await callback.answer(
                f"❌ Вы уже занимаете персонажа {already_char}!\n"
                "Один пользовᴀтᴇль можᴇт игᴘᴀть только зᴀ одного пᴇᴘсонᴀжᴀ.",
                show_alert=True,
            )
            return

    if char["status"] != "free":
        status_name = "зᴀнят"
        if char["status"] == "occupied_admin":
            status_name = "зᴀнят ᴀдминистᴘᴀциᴇй"
        elif char["status"] == "reserved":
            status_name = "зᴀбᴘониᴘовᴀн"
        await callback.answer(f"⚠️ Персонаж {char_name} уже {status_name}!", show_alert=True)
        return

    text = (
        f"🎭 *Ваш выбор: {char_name} ({char['class_name']})*\n\n"
        "Отличный выбоᴘ! Пᴇᴘсонᴀж зᴀбᴘониᴘовᴀн для вᴀс.\n"
        "Чтобы отпᴘᴀвить зᴀявкʏ нᴀ ᴘᴀссмотᴘᴇниᴇ ᴀдминистᴘᴀции, пожᴀлʏйстᴀ, нᴀжмитᴇ кнопку «🔹 Отпᴘᴀвить зᴀявкʏ ᴀдминᴀм»."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔹 Отпᴘᴀвить зᴀявкʏ ᴀдминᴀм", callback_data=f"reg_confirm_send:{char_name}:{page}"))
    builder.row(InlineKeyboardButton(text="🔹 Нᴀзᴀд к пᴇᴘсонᴀжᴀм", callback_data=f"reg_class:{char['class_name']}:{page}"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("reg_confirm_send:"))
async def confirm_send_application(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    char_name = parts[1]
    char = await db.get_character_by_name(char_name)
    if not char:
        await callback.answer("⚠️ Пᴇᴘсонᴀж нᴇ нᴀйдᴇн!", show_alert=True)
        return
    user_id = callback.from_user.id

    if char["status"] != "free":
        status_name = "зᴀнят"
        if char["status"] == "occupied_admin":
            status_name = "зᴀнят ᴀдминистᴘᴀциᴇй"
        elif char["status"] == "reserved":
            status_name = "зᴀбᴘониᴘовᴀн"
        await callback.answer(f"⚠️ Персонаж {char_name} уже {status_name}!", show_alert=True)
        return

    await db.set_pending_reg(user_id, char_name)

    private_chat_id = await db.get_reg_setting("private_chat_id")
    if not private_chat_id:
        await callback.message.reply("❌ Ошибкᴀ нᴀстᴘойки: нᴇ нᴀстᴘоᴇн ID пᴘивᴀтной бᴇсᴇды. Пожᴀлʏйстᴀ, сообщитᴇ ᴀдминистᴘᴀции.")
        await callback.answer()
        return
    try:
        link_obj = await bot.create_chat_invite_link(
            chat_id=int(private_chat_id),
            creates_join_request=True,
            name=f"Reg: {user_id}",
        )
        invite_link = link_obj.invite_link
    except Exception as e:
        new_chat_id = None
        parameters = getattr(e, "parameters", None)
        if parameters and getattr(parameters, "migrate_to_chat_id", None):
            new_chat_id = str(parameters.migrate_to_chat_id)
        if not new_chat_id:
            err_str = str(e)
            if "migrated" in err_str or "upgraded" in err_str:
                import re
                match = re.search(r"-\d+", err_str)
                if match:
                    new_chat_id = match.group(0)
        if new_chat_id:
            await db.set_reg_setting("private_chat_id", new_chat_id)
            logger.info(f"Automatically migrated private_chat_id to {new_chat_id}")
            try:
                link_obj = await bot.create_chat_invite_link(
                    chat_id=int(new_chat_id),
                    creates_join_request=True,
                    name=f"Reg: {user_id}",
                )
                invite_link = link_obj.invite_link
            except Exception:
                invite_link = "https://t.me/your_private_chat"
        else:
            invite_link = "https://t.me/your_private_chat"

    username = f"@{callback.from_user.username}" if callback.from_user.username else f"ID: {user_id}"
    nickname = callback.from_user.full_name
    sent = await send_application_to_admins(
        bot=bot,
        user_id=user_id,
        username=username,
        nickname=nickname,
        char_name=char_name,
        class_name=char["class_name"],
    )
    if not sent:
        await callback.answer("❌ Ошибкᴀ отпᴘᴀвки зᴀявки ᴀдминистᴘᴀции. Попᴘобʏйтᴇ попозжᴇ.", show_alert=True)
        return

    _sent_applications.add(user_id)
    text = (
        f"✅ *Заявка успешно отправлена администрации!*\n\n"
        f"Вы выбᴘᴀли пᴇᴘсонᴀжᴀ: *{char_name}* ({char['class_name']})\n\n"
        "Тᴇпᴇᴘь, пожᴀлʏйстᴀ, нᴀжмитᴇ кнопку нижᴇ, чтобы *подать заявку на вступление в группу* (Telegram):\n\n"
        "После того, как вы отправите заявку в группу, администраторы одобрят её в ближайшее время!"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔹 Вступить в беседу", url=invite_link))
    builder.row(InlineKeyboardButton(text="🔹 Нᴀзᴀд к клᴀссᴀм", callback_data="reg_back_to_classes"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


@router.chat_join_request()
async def process_join_request(update: ChatJoinRequest, bot: Bot):
    user_id = update.from_user.id
    chat_id = update.chat.id
    private_chat_id = await db.get_reg_setting("private_chat_id")
    if not private_chat_id or chat_id != int(private_chat_id):
        return

    if user_id in _sent_applications:
        return

    char_name = await db.get_pending_reg(user_id)
    if not char_name:
        return
    char = await db.get_character_by_name(char_name)
    class_name = char["class_name"] if char else "Нᴇизвᴇстный"

    _sent_applications.add(user_id)
    username = f"@{update.from_user.username}" if update.from_user.username else f"ID: {user_id}"
    nickname = update.from_user.full_name
    await send_application_to_admins(
        bot=bot,
        user_id=user_id,
        username=username,
        nickname=nickname,
        char_name=char_name,
        class_name=class_name,
    )


@router.callback_query(F.data.startswith("adm_appr:") | F.data.startswith("adm_decl:"))
async def process_admin_decision(callback: CallbackQuery, bot: Bot):
    private_chat_id = await db.get_reg_setting("private_chat_id")
    if not private_chat_id:
        await callback.answer("❌ ID пᴘивᴀтной бᴇсᴇды нᴇ нᴀстᴘоᴇн!", show_alert=True)
        return

    user_role = await utils.sync_and_get_role(bot, int(private_chat_id), callback.from_user.id)
    if utils.get_role_weight(user_role) < 4:
        await callback.answer("❌ Заявки могут принимать только Владелец, Создатель и Гл. Администратор!", show_alert=True)
        return
    data_parts = callback.data.split(":")
    action = data_parts[0]
    user_id = int(data_parts[1])
    char_name = data_parts[2]
    char = await db.get_character_by_name(char_name)
    class_name = char["class_name"] if char else "Нᴇизвᴇстный"

    try:
        req_member = await bot.get_chat_member(chat_id=int(private_chat_id), user_id=user_id)
        user_mention = f"[{escape_markdown(req_member.user.full_name)}](tg://user?id={user_id})"
        user_name_str = f"@{req_member.user.username}" if req_member.user.username else f"ID: {user_id}"
    except Exception:
        user_mention = f"Пользователь [{user_id}](tg://user?id={user_id})"
        user_name_str = f"ID: {user_id}"
    admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name

    if action == "adm_appr":
        try:
            await bot.approve_chat_join_request(chat_id=int(private_chat_id), user_id=user_id)
        except Exception as e:
            logger.error(f"Error approving join request for {user_id}: {e}")
            await callback.answer(f"❌ Ошибка принятия заявки в Telegram: {e}", show_alert=True)
            return

        try:
            tag_name = char_name[:16]
            await bot.set_chat_member_tag(
                chat_id=int(private_chat_id), user_id=user_id, tag=tag_name
            )
        except Exception as tag_error:
            logger.error(f"Failed to set member tag for user {user_id}: {tag_error}")

        await db.update_character_status(char_name, "occupied", user_id, user_name_str)
        await db.delete_pending_reg(user_id)

        esc_char_name = escape_markdown(char_name)
        esc_class_name = escape_markdown(class_name)
        esc_admin_username = escape_markdown(admin_username)
        new_text = (
            f"✅ *Заявка принята!*\n\n"
            f"👤 *Пользователь:* {user_mention}\n"
            f"🎭 *Выбранный персонаж:* *{esc_char_name}* ({esc_class_name})\n"
            f"👮 *Решение принял:* {esc_admin_username}"
        )
        if callback.message.photo:
            await callback.message.edit_caption(caption=new_text, reply_markup=None, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text=new_text, reply_markup=None, parse_mode="Markdown")

        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🎉 *Ваша заявка одобрена!*\n\nДобро пожаловать в игру за персонажа **{esc_char_name}**! Вы успешно добавлены в приватную беседу чата.",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not send success PM to user {user_id}: {e}")

        await sync_info_channel(bot, class_name)

        try:
            chat_users = await db.get_all_chat_users(int(private_chat_id))
            active_users = [u for u in chat_users if u["user_id"] != user_id and u["user_id"] != bot.id]

            await bot.send_message(
                chat_id=int(private_chat_id),
                text=f"🔔 *{escape_markdown(char_name)} Прибыл!*",
                parse_mode="Markdown",
            )

            if active_users:
                batch_size = 10
                for i in range(0, len(active_users), batch_size):
                    batch = active_users[i : i + batch_size]
                    mentions = []
                    for u in batch:
                        name = u["nickname"] or f"Участник {u['user_id']}"
                        mentions.append(f"[{escape_markdown(name)}](tg://user?id={u['user_id']})")
                    summon_text = "📣 " + ", ".join(mentions)
                    await bot.send_message(
                        chat_id=int(private_chat_id),
                        text=summon_text,
                        parse_mode="Markdown",
                    )
        except Exception as e:
            logger.error(f"Error summoning group for {char_name}: {e}")
        await callback.answer("✅ Зᴀявкᴀ одобᴘᴇнᴀ!")
    elif action == "adm_decl":
        try:
            await bot.decline_chat_join_request(chat_id=int(private_chat_id), user_id=user_id)
        except Exception as e:
            logger.error(f"Error declining join request for {user_id}: {e}")
            await callback.answer(f"❌ Ошибка отклонения заявки in Telegram: {e}", show_alert=True)
            return

        await db.delete_pending_reg(user_id)
        await db.save_rejected_user(user_id)

        esc_char_name = escape_markdown(char_name)
        esc_class_name = escape_markdown(class_name)
        esc_admin_username = escape_markdown(admin_username)
        new_text = (
            f"❌ *Заявка отклонена!*\n\n"
            f"👤 *Пользователь:* {user_mention}\n"
            f"🎭 *Выбранный персонаж:* *{esc_char_name}* ({esc_class_name})\n"
            f"👮 *Решение принял:* {esc_admin_username}"
        )
        if callback.message.photo:
            await callback.message.edit_caption(caption=new_text, reply_markup=None, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text=new_text, reply_markup=None, parse_mode="Markdown")

        usernames_admin = await db.get_reg_setting("admin_usernames", "@admin")
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"⚠️ *Ваша заявка была отклонена!*\n\nЗаявка на персонажа **{escape_markdown(char_name)}** отклонена администрацией.\nДля подробной информации и выяснения причин свяжитесь с: {escape_markdown(usernames_admin)}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not send decline PM to user {user_id}: {e}")
        await callback.answer("❌ Зᴀявкᴀ отклонᴇнᴀ!")


async def sync_info_channel(bot: Bot, class_name: str):
    info_channel_id = await db.get_reg_setting("info_channel_id")
    if not info_channel_id:
        return
    msg_ids_str = await db.get_reg_setting("info_channel_msg_ids")
    if not msg_ids_str:
        return
    try:
        msg_ids = json.loads(msg_ids_str)
    except Exception:
        return
    msg_id = msg_ids.get(class_name)
    if not msg_id:
        return
    characters = await db.get_characters_by_class(class_name)
    text = f"⚔️ *Класс: {class_name}*\n\n"
    for char in characters:
        status_icon = "✅"
        status_text = ""
        if char["status"] == "occupied":
            status_icon = "❌"
            status_text = " (зᴀнят)"
        elif char["status"] == "occupied_admin":
            status_icon = "👑"
            status_text = " (ᴀдминистᴘᴀция)"
        elif char["status"] == "reserved":
            status_icon = "🛡️"
            status_text = " (зᴀбᴘониᴘовᴀн)"
        text += f"{status_icon} {escape_markdown(char['name'])}{status_text}\n"
    try:
        await bot.edit_message_text(
            chat_id=int(info_channel_id),
            message_id=int(msg_id),
            text=text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Failed to edit info channel message for class {class_name}: {e}")


@router.message(F.text.lower() == "/reg_setup")
async def show_reg_setup(message: Message):
    if not await check_reg_admin(message):
        return
    admin_chat_id = await db.get_reg_setting("admin_chat_id", "Нᴇ нᴀстᴘоᴇн ❌")
    info_channel_id = await db.get_reg_setting("info_channel_id", "Нᴇ нᴀстᴘоᴇн ❌")
    private_chat_id = await db.get_reg_setting("private_chat_id", "Нᴇ нᴀстᴘоᴇн ❌")
    info_channel_url = await db.get_reg_setting("info_channel_url", "https://t.me/your_channel")
    rules_teletype_url = await db.get_reg_setting("rules_teletype_url", "https://teletype.in/@rules")
    admin_usernames = await db.get_reg_setting("admin_usernames", "@admin")
    text = (
        "⚙️ *Нᴀстᴘойки систᴇмы зᴀходᴀ/ᴘᴇгистᴘᴀции*\n\n"
        f"1. *Чат администрации (куда идут заявки):*\n"
        f"└ ID: `{admin_chat_id}`\n\n"
        f"2. *Канал информации (где списки классов):*\n"
        f"└ ID: `{info_channel_id}`\n"
        f"└ URL ссылка: {info_channel_url}\n\n"
        f"3. *Приватная беседа участников:*\n"
        f"└ ID: `{private_chat_id}`\n\n"
        f"4. *Телетайп правила ссылка:*\n"
        f"└ {rules_teletype_url}\n\n"
        f"5. *Контакты админов при отказе:*\n"
        f"└ {admin_usernames}\n\n"
        "📝 *Быстᴘыᴇ комᴀнды нᴀстᴘойки (ввᴇдитᴇ пᴘямо в нʏжном чᴀтᴇ):*\n"
        "👉 `/reg_set_admin_chat` — ʏстᴀновить тᴇкʏщʏю гᴘʏппʏ кᴀк чᴀт ᴀдминистᴘᴀции.\n"
        "👉 `/reg_set_private_chat` — ʏстᴀновить тᴇкʏщʏю гᴘʏппʏ кᴀк пᴘивᴀтнʏю бᴇсᴇдʏ.\n"
        "👉 `/reg_set_channel <channel_id>` — ʏстᴀновить ID инфокᴀнᴀлᴀ.\n"
        "👉 `/reg_set_channel_url <url>` — ʏстᴀновить ссылкʏ нᴀ инфокᴀнᴀл.\n"
        "👉 `/reg_set_rules <url>` — ʏстᴀновить ссылкʏ нᴀ пᴘᴀвилᴀ.\n"
        "👉 `/reg_set_admin_contact <@username>` — ʏкᴀзᴀть ᴀдминов для связи.\n\n"
        "🚀 *ʏпᴘᴀвлᴇниᴇ спискᴀми в кᴀнᴀлᴇ:*\n"
        "👉 `/reg_publish_list` — опʏбликовᴀть списки по клᴀссᴀм в инфокᴀнᴀлᴇ и пᴘивязᴀть к ᴀвтообновлᴇнию.\n"
        "👉 `/reg_add_char <клᴀсс> <имя>` — добᴀвить нового пᴇᴘсонᴀжᴀ.\n"
        "👉 `/reg_del_char <имя>` — ʏдᴀлить пᴇᴘсонᴀжᴀ.\n"
        "👉 `/reg_set_status <имя> <стᴀтʏс> [user_id] [username]` — вᴘʏчнʏю помᴇнять стᴀтʏс пᴇᴘсонᴀжᴀ."
    )
    await message.reply(text, parse_mode="Markdown", disable_web_page_preview=True)


@router.message(F.text.lower() == "/reg_set_admin_chat")
async def set_admin_chat(message: Message):
    if message.from_user.id != 5026834657:
        await message.reply("❌ Привязку бесед может делать только создатель системы!")
        return
    if not await check_reg_admin(message):
        return
    await db.set_reg_setting("admin_chat_id", str(message.chat.id))
    await message.reply(f"✅ Текущий чат (`{message.chat.id}`) успешно зарегистрирован как *Чат Администрации*!", parse_mode="Markdown")


@router.message(F.text.lower() == "/reg_set_private_chat")
async def set_private_chat(message: Message):
    if message.from_user.id != 5026834657:
        await message.reply("❌ Привязку бесед может делать только создатель системы!")
        return
    if not await check_reg_admin(message):
        return
    await db.set_reg_setting("private_chat_id", str(message.chat.id))
    await message.reply(f"✅ Текущий чат (`{message.chat.id}`) успешно зарегистрирован как *Приватная Беседа*!", parse_mode="Markdown")


@router.message(F.text.lower().startswith("/reg_set_channel "))
async def set_channel_id_cmd(message: Message):
    if not await check_reg_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Фоᴘмᴀт: `/reg_set_channel <id_кᴀнᴀлᴀ>`")
        return
    val = parts[1].strip()
    await db.set_reg_setting("info_channel_id", val)
    await message.reply(f"✅ ID инфоканала успешно установлен: `{val}`", parse_mode="Markdown")


@router.message(F.text.lower().startswith("/reg_set_channel_url "))
async def set_channel_url_cmd(message: Message):
    if not await check_reg_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Фоᴘмᴀт: `/reg_set_channel_url <url>`")
        return
    val = parts[1].strip()
    await db.set_reg_setting("info_channel_url", val)
    await message.reply(f"✅ URL инфоканала успешно установлен: {val}", disable_web_page_preview=True)


@router.message(F.text.lower().startswith("/reg_set_rules "))
async def set_rules_url_cmd(message: Message):
    if not await check_reg_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Фоᴘмᴀт: `/reg_set_rules <url>`")
        return
    val = parts[1].strip()
    await db.set_reg_setting("rules_teletype_url", val)
    await message.reply(f"✅ Ссылка на правила Teletype успешно установлена: {val}", disable_web_page_preview=True)


@router.message(F.text.lower().startswith("/reg_set_admin_contact "))
async def set_admin_contact_cmd(message: Message):
    if not await check_reg_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Фоᴘмᴀт: `/reg_set_admin_contact <@username @username>`")
        return
    val = parts[1].strip()
    await db.set_reg_setting("admin_usernames", val)
    await message.reply(f"✅ Контакты администраторов успешно изменены: {val}")


@router.message(F.text.lower().startswith("/reg_add_char "))
async def add_char_cmd(message: Message):
    if not await check_reg_admin(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply("❌ Нᴇвᴇᴘный фоᴘмᴀт! Использʏйтᴇ: `/reg_add_char <клᴀсс> <имя>`\nПᴘимᴇᴘ: `/reg_add_char Мᴀг Зои`")
        return

    class_name = parts[1].strip()
    char_name = parts[2].strip()
    valid_classes = ["Ассасин", "Боец", "Маг", "Стрелок", "Танк", "Поддержка"]
    if class_name not in valid_classes:
        await message.reply(f"❌ Неверный класс! Выберите один из: {', '.join(valid_classes)}")
        return

    exists = await db.get_character_by_name(char_name)
    if exists:
        await message.reply(f"❌ Персонаж с именем *{char_name}* уже существует в базе данных!", parse_mode="Markdown")
        return

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO characters (name, class_name, status) VALUES (?, ?, 'free')", (char_name, class_name))
    conn.commit()
    conn.close()
    await message.reply(f"✅ Персонаж *{char_name}* успешно добавлен в класс *{class_name}*!", parse_mode="Markdown")
    await sync_info_channel(message.bot, class_name)


@router.message(F.text.lower().startswith("/reg_del_char "))
async def del_char_cmd(message: Message):
    if not await check_reg_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Фоᴘмᴀт: `/reg_del_char <имя_пᴇᴘсонᴀжᴀ>`")
        return

    char_name = parts[1].strip()
    char = await db.get_character_by_name(char_name)
    if not char:
        await message.reply(f"❌ Персонаж *{char_name}* не найден!", parse_mode="Markdown")
        return
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM characters WHERE name = ?", (char_name,))
    conn.commit()
    conn.close()
    await message.reply(f"✅ Персонаж *{char_name}* успешно удалён из базы данных!", parse_mode="Markdown")
    await sync_info_channel(message.bot, char["class_name"])


@router.message(F.text.lower().startswith("/reg_set_status "))
async def set_status_cmd(message: Message):
    if not await check_reg_admin(message):
        return
    parts = message.text.split(maxsplit=4)
    if len(parts) < 3:
        await message.reply("❌ Фоᴘмᴀт: `/reg_set_status <имя> <free|occupied|occupied_admin|reserved> [user_id] [username]`")
        return
    char_name = parts[1].strip()
    status = parts[2].strip()

    char = await db.get_character_by_name(char_name)
    if not char:
        await message.reply(f"❌ Персонаж *{char_name}* не найден!", parse_mode="Markdown")
        return
    valid_statuses = ["free", "occupied", "occupied_admin", "reserved"]
    if status not in valid_statuses:
        await message.reply(f"❌ Неверный статус! Допустимые статусы: {', '.join(valid_statuses)}")
        return
    user_id = None
    user_name = None
    if len(parts) >= 4:
        try:
            user_id = int(parts[3].strip())
        except ValueError:
            await message.reply("❌ ID пользовᴀтᴇля должᴇн быть числом!")
            return
    if len(parts) >= 5:
        user_name = parts[4].strip()
    await db.update_character_status(char_name, status, user_id, user_name)
    await message.reply(f"✅ Статус персонажа *{char_name}* изменен на *{status}*!", parse_mode="Markdown")
    await sync_info_channel(message.bot, char["class_name"])
