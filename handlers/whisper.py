import uuid

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

import tgbot.database as db

router = Router()
draft_whispers = {}


@router.inline_query()
async def process_inline_whisper(inline_query: InlineQuery):
    query = inline_query.query.strip()
    sender_id = inline_query.from_user.id
    sender_name = inline_query.from_user.full_name

    global draft_whispers
    if len(draft_whispers) > 5000:
        draft_whispers.clear()

    members = await db.get_shared_chat_members(sender_id)

    if not query:
        results = []
        for m in members:
            username = m["username"]
            nickname = m["nickname"] or f"Пользователь {m['user_id']}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"Выбрать {nickname} 🎯",
                            switch_inline_query_current_chat=f"@{username} ",
                        )
                    ]
                ]
            )
            results.append(
                InlineQueryResultArticle(
                    id=f"sel_{m['user_id']}",
                    title=f"👤 {nickname} (@{username})",
                    description="Нᴀжмитᴇ кнопкʏ нижᴇ, чтобы выбᴘᴀть этого ʏчᴀстникᴀ",
                    input_message_content=InputTextMessageContent(
                        message_text=f"🤐 Выбираю @{username} для отправки шёпота...",
                        parse_mode="HTML",
                    ),
                    reply_markup=keyboard,
                )
            )
        await inline_query.answer(results, cache_time=0, is_personal=True)
        return

    parts = query.split(maxsplit=2)
    first_word = parts[0].strip()
    has_explicit_recipient = False
    target_username = None
    message_text = None

    if first_word.startswith("@") and len(parts) >= 2:
        has_explicit_recipient = True
        target_username = first_word.replace("@", "").strip()
        message_text = query[len(first_word) :].strip()
    elif first_word.lower() in ["whisper", "шёпот", "шепот"] and len(parts) >= 3:
        has_explicit_recipient = True
        target_username = parts[1].replace("@", "").strip()
        message_text = parts[2].strip()
    else:
        clean_first_word = first_word.lower().replace("@", "")
        matching_member = None
        for m in members:
            uname = (m["username"] or "").lower()
            nname = (m["nickname"] or "").lower()
            if clean_first_word in [uname, nname]:
                matching_member = m
                break
        if matching_member:
            parts_direct = query.split(maxsplit=1)
            if len(parts_direct) >= 2:
                has_explicit_recipient = True
                target_username = matching_member["username"]
                message_text = parts_direct[1].strip()

    if has_explicit_recipient and target_username and message_text:
        whisper_id = str(uuid.uuid4())[:18]

        draft_whispers[whisper_id] = {
            "sender_id": sender_id,
            "sender_name": sender_name,
            "target_username": target_username,
            "message_text": message_text,
        }
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Читᴀть шёпот 👁", callback_data=f"whisper:{whisper_id}")]
            ]
        )
        results = [
            InlineQueryResultArticle(
                id=whisper_id,
                title=f"Отправить шёпот для @{target_username}",
                description=f"Текст сообщения: {message_text[:30]}...",
                input_message_content=InputTextMessageContent(
                    message_text=f"🤐 <b>Шёпот для @{target_username}</b>\n<i>(нажмите кнопку ниже, чтобы прочесть)</i>",
                    parse_mode="HTML",
                ),
                reply_markup=keyboard,
            )
        ]
        await inline_query.answer(results, cache_time=0, is_personal=True)
        return

    results = []
    for m in members:
        username = m["username"]
        nickname = m["nickname"] or f"Пользователь {m['user_id']}"
        whisper_id = str(uuid.uuid4())[:18]

        draft_whispers[whisper_id] = {
            "sender_id": sender_id,
            "sender_name": sender_name,
            "target_username": username,
            "message_text": query,
        }
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Читᴀть шёпот 👁", callback_data=f"whisper:{whisper_id}")]
            ]
        )
        results.append(
            InlineQueryResultArticle(
                id=whisper_id,
                title=f"👤 Отправить для {nickname} (@{username})",
                description=f"Текст: {query[:40]}...",
                input_message_content=InputTextMessageContent(
                    message_text=f"🤐 <b>Шёпот для @{username}</b>\n<i>(нажмите кнопку ниже, чтобы прочесть)</i>",
                    parse_mode="HTML",
                ),
                reply_markup=keyboard,
            )
        )

    await inline_query.answer(results, cache_time=0, is_personal=True)


@router.callback_query(F.data.startswith("whisper:"))
async def read_whisper(callback: CallbackQuery):
    whisper_id = callback.data.split(":")[1]
    whisper = await db.get_whisper(whisper_id)
    if not whisper:
        whisper_draft = draft_whispers.get(whisper_id)
        if whisper_draft:
            await db.save_whisper(
                whisper_id=whisper_id,
                sender_id=whisper_draft["sender_id"],
                sender_name=whisper_draft["sender_name"],
                target_username=whisper_draft["target_username"],
                message_text=whisper_draft["message_text"],
            )
            whisper = whisper_draft
        else:
            await callback.answer(text="❌ Ошибкᴀ: этот шёпот нᴇ нᴀйдᴇн или ʏстᴀᴘᴇл!", show_alert=True)
            return

    sender_id = whisper["sender_id"]
    target_uname = whisper["target_username"].lower()
    sender_name = whisper["sender_name"]
    clicker_id = callback.from_user.id
    clicker_uname = (callback.from_user.username or "").lower()

    is_sender = clicker_id == sender_id
    is_recipient = (clicker_uname == target_uname) or (str(clicker_id) == target_uname)
    if is_sender or is_recipient:
        await callback.answer(
            text=f"✉️ [Шёпот от {sender_name}]:\n\n{whisper['message_text']}",
            show_alert=True,
        )
    else:
        await callback.answer(text="🤫 Этот шёпот пᴘᴇднᴀзнᴀчᴀᴇтся нᴇ вᴀм!", show_alert=True)
