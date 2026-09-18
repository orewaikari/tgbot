import asyncio
import random

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import tgbot.database as db

router = Router()

CROC_WORDS = [
    "алгоритм", "база данных", "сервер", "питон", "роутер", "клавиатура", "сисадмин",
    "скрипт", "кофеварка", "телеграм бот", "монитор", "двухфакторная аутентификация",
    "микросервис", "фреймворк", "репозиторий", "коммит", "веб-сервер", "кодинг",
    "виртуальное окружение", "интернет", "баг", "замыкание", "асинхронность",
]

ACTIVE_CROC = {}
ACTIVE_MAFIA = {}


@router.message(F.text.lower().in_(["!крокодил", "крокодил", "/крокодил", "/crocodile", "crocodile"]))
async def start_croc(message: Message):
    chat_id = message.chat.id
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("🐊 В Крокодила можно играть только в группах!")
        return

    if chat_id in ACTIVE_CROC:
        await message.reply("⚠️ Игра уже идет в этом чате! Напишите `!стоп крокодил` чтобы прервать её.")
        return

    host_id = message.from_user.id
    host_name = message.from_user.full_name
    word = random.choice(CROC_WORDS)

    try:
        await message.bot.send_message(
            chat_id=host_id,
            text=f"🐊 *Вы запустили Крокодила!*\n\nВаше секретное слово: *{word}*\n\nОбъясняйте его в группе! "
                 f"Участники должны угадать слово в чате.",
            parse_mode="Markdown",
        )
    except Exception:
        await message.reply(
            "❌ *Ошибка запуска!* Бот не может отправить вам слово в ЛС. "
            "Пожалуйста, запустите бота в личных сообщениях (@вашего_бота) и попробуйте снова! 🥺",
            parse_mode="Markdown",
        )
        return

    ACTIVE_CROC[chat_id] = {
        "word": word,
        "host_id": host_id,
        "host_name": host_name,
    }

    await message.reply(
        f"🐊 *ИГРА КРОКОДИЛ НАЧАЛАСЬ!* 🐊\n\n"
        f"👤 Ведущий: *{host_name}*\n"
        f"Задача ведущего — объяснить слово в реальной жизни (или рисовать, показывать), "
        f"а участники должны угадать его в чате!\n\n"
        f"🤫 *Секретное слово отправлено ведущему в ЛС!*",
        parse_mode="Markdown",
    )


@router.message(F.text.lower().in_(["!стоп крокодил", "стоп крокодил", "/стоп крокодил"]))
async def stop_croc(message: Message):
    chat_id = message.chat.id
    if chat_id in ACTIVE_CROC:
        ACTIVE_CROC.pop(chat_id)
        await message.reply("🐊 Игра Крокодил остановлена!")
    else:
        await message.reply("Крокодил сейчас не запущен в этом чате.")


def is_croc_active(message: Message) -> bool:
    return message.chat.id in ACTIVE_CROC


@router.message(F.chat.type.in_(["group", "supergroup"]), is_croc_active)
async def check_croc_guess(message: Message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE_CROC:
        return

    game = ACTIVE_CROC[chat_id]

    if message.from_user.id == game["host_id"]:
        return

    guess = message.text.strip().lower() if message.text else ""
    target = game["word"].strip().lower()

    if guess == target:
        winner_id = message.from_user.id
        winner_name = message.from_user.full_name

        reward = 100
        new_balance = await db.add_coins(winner_id, chat_id, reward)

        ACTIVE_CROC.pop(chat_id)

        await message.reply(
            f"🎉 *ПРАВИЛЬНО!* 🎉\n\n"
            f"👤 *{winner_name}* угадал секретное слово: *{game['word']}*!\n"
            f"🪙 Награда: *{reward}* золотых монет начислено на счет!\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )


@router.message(F.text.lower().in_([
    "!мафия", "мафия", "/мафия", "мафия старт", "!мафия старт", "/мафия старт", "mafia", "/mafia"
]))
async def start_mafia(message: Message):
    chat_id = message.chat.id
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("🕵️‍♂️ В Мафию можно играть только в группах!")
        return

    if chat_id in ACTIVE_MAFIA:
        await message.reply("⚠️ Мафия уже запущена или регистрируется в этом чате!")
        return

    ACTIVE_MAFIA[chat_id] = {
        "phase": "registration",
        "players": [],
        "votes": {},
        "mafia_target": None,
        "sheriff_checked": None,
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Участвовать 🙋‍♂️", callback_data=f"mafia_join:{chat_id}")]
    ])

    await message.reply(
        f"🕵️‍♂️ *ИГРА МАФИЯ: РЕГИСТРАЦИЯ ИГРОКОВ!* 🕵️‍♂️\n\n"
        f"Уважаемые жители, мафия пробралась в наш уютный чат!\n"
        f"Чтобы вступить в борьбу, нажмите кнопку ниже.\n\n"
        f"⚠️ *ВАЖНО*: Убедитесь, что вы запустили этого бота в ЛС, иначе он не сможет выдать вам роль!\n"
        f"⏱ Регистрация завершится через 45 секунд, либо напишите `!мафия запуск`.",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

    await asyncio.sleep(45)
    await run_mafia_auto_start(chat_id, message.bot)


@router.callback_query(F.data.startswith("mafia_join:"))
async def mafia_join_cb(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name

    if chat_id not in ACTIVE_MAFIA:
        await callback.answer("⏳ Регистрация уже завершена!", show_alert=True)
        return

    game = ACTIVE_MAFIA[chat_id]
    if game["phase"] != "registration":
        await callback.answer("Игра уже в процессе!", show_alert=True)
        return

    if any(p["id"] == user_id for p in game["players"]):
        await callback.answer("Вы уже зарегистрированы!", show_alert=True)
        return

    try:
        await callback.bot.send_message(user_id, "🔔 Вы успешно зарегистрированы на игру Мафия!")
        pm_active = True
    except Exception:
        pm_active = False
        await callback.answer("❌ Сначала запустите бота в ЛС (@вашего_бота)!", show_alert=True)
        return

    game["players"].append({
        "id": user_id,
        "name": user_name,
        "role": None,
        "alive": True,
        "pm_active": pm_active,
    })

    await callback.answer("Вы успешно зарегистрированы! 🎉")

    players_list = "\n".join([f"👤 {p['name']}" for p in game["players"]])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Участвовать 🙋‍♂️", callback_data=f"mafia_join:{chat_id}")]
    ])
    try:
        await callback.message.edit_text(
            f"🕵️‍♂️ *ИГРА МАФИЯ: РЕГИСТРАЦИЯ ИГРОКОВ!* 🕵️‍♂️\n\n"
            f"Зарегистрированные жители ({len(game['players'])}):\n{players_list}\n\n"
            f"⏱ Регистрация идет...",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    except Exception:
        pass


@router.message(F.text.lower().in_(["!мафия запуск", "мафия запуск", "/мафия запуск"]))
async def manual_mafia_start(message: Message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE_MAFIA:
        return
    await run_mafia_auto_start(chat_id, message.bot)


async def run_mafia_auto_start(chat_id: int, bot: Bot):
    if chat_id not in ACTIVE_MAFIA:
        return

    game = ACTIVE_MAFIA[chat_id]
    if game["phase"] != "registration":
        return

    if len(game["players"]) < 3:
        ACTIVE_MAFIA.pop(chat_id, None)
        await bot.send_message(
            chat_id,
            "❌ *Игра отменена!* Не набралось минимальное количество участников (требуется от 3 игроков).",
            parse_mode="Markdown",
        )
        return

    players = game["players"]
    random.shuffle(players)

    num_mafia = 2 if len(players) >= 6 else 1

    for i, p in enumerate(players):
        if i < num_mafia:
            p["role"] = "Мафия"
        elif i == num_mafia:
            p["role"] = "Шериф"
        else:
            p["role"] = "Мирный житель"

    game["phase"] = "night"

    for p in players:
        if p["role"] == "Мафия":
            role_desc = "🕵️‍♂️ Вы — *МАФИЯ*!\nВаша цель — ликвидировать мирных жителей и шерифа. Ночью выбирайте жертву вместе с другими мафиози!"
        elif p["role"] == "Шериф":
            role_desc = "🔎 Вы — *ШЕРИФ*!\nВаша цель — обнаружить мафию. Ночью проводите проверки игроков!"
        else:
            role_desc = "👤 Вы — *МИРНЫЙ ЖИТЕЛЬ*!\nВаша цель — вычислить мафию на дневном обсуждении и казнить её голосованием."

        try:
            await bot.send_message(p["id"], f"🎭 *ВАША СЕКРЕТНАЯ РОЛЬ:* \n\n{role_desc}", parse_mode="Markdown")
        except Exception:
            pass

    await bot.send_message(
        chat_id,
        f"🎮 *Игра началась! Роли распределены в ЛС.* 🎮\n\n"
        f"Количество игроков: {len(players)}\n"
        f"Мафии в городе: {num_mafia}\n"
        f"Шериф вышел на охоту.\n\n"
        f"🌃 *Наступает ночь...* Город засыпает. Шериф и Мафия делают свои ходы в ЛС!",
        parse_mode="Markdown",
    )

    await run_mafia_night(chat_id, bot)


async def run_mafia_night(chat_id: int, bot: Bot):
    game = ACTIVE_MAFIA[chat_id]
    players = game["players"]

    game["mafia_target"] = None
    game["sheriff_checked"] = None

    mafia_buttons = []
    sheriff_buttons = []

    alive_players = [p for p in players if p["alive"]]

    for p in alive_players:
        if p["role"] != "Мафия":
            mafia_buttons.append([InlineKeyboardButton(text=p["name"], callback_data=f"maf_kill:{chat_id}:{p['id']}")])
        if p["role"] != "Шериф":
            sheriff_buttons.append([InlineKeyboardButton(text=p["name"], callback_data=f"she_check:{chat_id}:{p['id']}")])

    mafia_kb = InlineKeyboardMarkup(inline_keyboard=mafia_buttons)
    sheriff_kb = InlineKeyboardMarkup(inline_keyboard=sheriff_buttons)

    for p in alive_players:
        if p["role"] == "Мафия":
            try:
                await bot.send_message(
                    p["id"],
                    "🌃 *Ночной ход Мафии:* \nВыберите, кого убрать этой ночью:",
                    reply_markup=mafia_kb,
                    parse_mode="Markdown",
                )
            except Exception:
                pass
        elif p["role"] == "Шериф":
            try:
                await bot.send_message(
                    p["id"],
                    "🌃 *Ночной ход Шерифа:* \nВыберите игрока для проверки на мафиозность:",
                    reply_markup=sheriff_kb,
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    await asyncio.sleep(25)
    await run_mafia_day(chat_id, bot)


@router.callback_query(F.data.startswith("maf_kill:") | F.data.startswith("she_check:"))
async def mafia_night_actions(callback: CallbackQuery):
    data = callback.data.split(":")
    action = data[0]
    chat_id = int(data[1])
    target_id = int(data[2])

    if chat_id not in ACTIVE_MAFIA:
        await callback.answer("Игра уже завершена!")
        return

    game = ACTIVE_MAFIA[chat_id]

    target_p = next((p for p in game["players"] if p["id"] == target_id), None)
    target_name = target_p["name"] if target_p else "Неизвестный"

    if action == "maf_kill":
        game["mafia_target"] = target_id
        await callback.message.edit_text(f"🎯 Вы выбрали цель на ликвидацию: *{target_name}*.", parse_mode="Markdown")
        await callback.answer("Выбор принят!")
    elif action == "she_check":
        game["sheriff_checked"] = target_id
        role = target_p["role"] if target_p else "Мирный житель"

        is_maf = "Да (Мафия!) 🕵️‍♂️" if role == "Мафия" else "Нет (Мирный!) 👤"
        await callback.message.edit_text(f"🔎 Проверка: Игрок *{target_name}*.\nРезультат: *{is_maf}*", parse_mode="Markdown")
        await callback.answer("Проверка проведена!")


async def run_mafia_day(chat_id: int, bot: Bot):
    if chat_id not in ACTIVE_MAFIA:
        return

    game = ACTIVE_MAFIA[chat_id]
    if game["phase"] != "night":
        return

    game["phase"] = "day"
    players = game["players"]

    target_id = game["mafia_target"]
    killed_p = next((p for p in players if p["id"] == target_id), None) if target_id else None

    morning_text = "🌅 *УТРО НАСТУПИЛО!* Все просыпаются... \n\n"

    if killed_p and killed_p["alive"]:
        killed_p["alive"] = False
        morning_text += f"☠️ К сожалению, этой ночью Мафия жестоко расправилась с игроком *{killed_p['name']}*! У него была роль: *{killed_p['role']}*.\n"
    else:
        morning_text += "🕊 Какая прекрасная ночь! Никто не пострадал!\n"

    await bot.send_message(chat_id, morning_text, parse_mode="Markdown")

    if await check_mafia_win_conditions(chat_id, bot):
        return

    await bot.send_message(
        chat_id,
        "🗣 *ДНЕВНЫЕ ДЕБАТЫ И ГОЛОСОВАНИЕ!* 🗣\n\n"
        "Обсудите в чате, кто является Мафией. \n"
        "Через 30 секунд запустится голосование, где вы выберете, кого казнить!",
        parse_mode="Markdown",
    )

    await asyncio.sleep(30)
    await run_mafia_voting(chat_id, bot)


async def run_mafia_voting(chat_id: int, bot: Bot):
    if chat_id not in ACTIVE_MAFIA:
        return

    game = ACTIVE_MAFIA[chat_id]
    players = game["players"]

    game["votes"] = {}

    vote_buttons = []
    alive_players = [p for p in players if p["alive"]]

    for p in alive_players:
        vote_buttons.append([InlineKeyboardButton(text=f"Казнить {p['name']}", callback_data=f"maf_vote:{chat_id}:{p['id']}")])

    vote_kb = InlineKeyboardMarkup(inline_keyboard=vote_buttons)

    await bot.send_message(
        chat_id,
        "🗳 *ВРЕМЯ ДНЕВНОГО ГОЛОСОВАНИЯ!* 🗳\n"
        "Выберите подозреваемого из кнопок ниже. У вас есть 25 секунд!",
        reply_markup=vote_kb,
        parse_mode="Markdown",
    )

    await asyncio.sleep(25)
    await process_mafia_voting_results(chat_id, bot)


@router.callback_query(F.data.startswith("maf_vote:"))
async def mafia_vote_cb(callback: CallbackQuery):
    data = callback.data.split(":")
    chat_id = int(data[1])
    target_id = int(data[2])
    voter_id = callback.from_user.id

    if chat_id not in ACTIVE_MAFIA:
        await callback.answer("Игра завершена!")
        return

    game = ACTIVE_MAFIA[chat_id]

    voter = next((p for p in game["players"] if p["id"] == voter_id), None)
    if not voter or not voter["alive"]:
        await callback.answer("❌ Мертвые не могут голосовать!", show_alert=True)
        return

    game["votes"][voter_id] = target_id
    await callback.answer("Голос принят!")


async def process_mafia_voting_results(chat_id: int, bot: Bot):
    if chat_id not in ACTIVE_MAFIA:
        return

    game = ACTIVE_MAFIA[chat_id]
    players = game["players"]
    votes = game["votes"]

    if not votes:
        await bot.send_message(
            chat_id,
            "🗳 *Голосование сорвано!* Никто не проголосовал. День прошел впустую...",
            parse_mode="Markdown",
        )
        game["phase"] = "night"
        await bot.send_message(chat_id, "🌃 *Наступает ночь...* Все жители снова засыпают.", parse_mode="Markdown")
        await run_mafia_night(chat_id, bot)
        return

    tallies = {}
    for voter_id, target_id in votes.items():
        tallies[target_id] = tallies.get(target_id, 0) + 1

    max_votes = -1
    lynched_id = None
    is_tie = False

    for tid, count in tallies.items():
        if count > max_votes:
            max_votes = count
            lynched_id = tid
            is_tie = False
        elif count == max_votes:
            is_tie = True

    if is_tie:
        await bot.send_message(
            chat_id,
            "🗳 *Ничья!* Голоса разделились поровну. Жители не смогли прийти к единому решению. Казнь отменяется!",
            parse_mode="Markdown",
        )
    else:
        lynched_p = next((p for p in players if p["id"] == lynched_id), None)
        if lynched_p:
            lynched_p["alive"] = False
            await bot.send_message(
                chat_id,
                f"⚖️ *Решение жителей принято!* \n"
                f"По результатам голосования, на площади был казнен игрок *{lynched_p['name']}*!\n"
                f"🛡 Его роль была: *{lynched_p['role']}*.",
                parse_mode="Markdown",
            )

    if await check_mafia_win_conditions(chat_id, bot):
        return

    game["phase"] = "night"
    await bot.send_message(chat_id, "🌃 *Наступает ночь...* Город засыпает.", parse_mode="Markdown")
    await run_mafia_night(chat_id, bot)


async def check_mafia_win_conditions(chat_id: int, bot: Bot) -> bool:
    if chat_id not in ACTIVE_MAFIA:
        return True

    game = ACTIVE_MAFIA[chat_id]
    players = game["players"]

    mafia_alive = [p for p in players if p["alive"] and p["role"] == "Мафия"]
    citizens_alive = [p for p in players if p["alive"] and p["role"] != "Мафия"]

    if not mafia_alive:
        for p in players:
            reward = 200 if p["alive"] else 100
            if p["role"] != "Мафия":
                await db.add_coins(p["id"], chat_id, reward)

        ACTIVE_MAFIA.pop(chat_id, None)
        await bot.send_message(
            chat_id,
            "🎉 *ПОБЕДА МИРНЫХ ЖИТЕЛЕЙ!* 🎉\n\n"
            "🕵️‍♂️ Вся мафия успешно нейтрализована!\n"
            "🪙 Мирным гражданам выплачена компенсация за мужество:\n"
            "• Выжившим: *200* монет\n"
            "• Погибшим: *100* монет\n\n"
            "Поздравляем! 🏆",
            parse_mode="Markdown",
        )
        return True

    if len(mafia_alive) >= len(citizens_alive):
        for p in players:
            if p["role"] == "Мафия":
                reward = 300 if p["alive"] else 150
                await db.add_coins(p["id"], chat_id, reward)

        ACTIVE_MAFIA.pop(chat_id, None)
        await bot.send_message(
            chat_id,
            "🩸 *ПОБЕДА МАФИИ!* 🩸\n\n"
            "🕵️‍♂️ Мафиози взяли полный контроль над чатом и захватили все ресурсы!\n"
            "🪙 Членам синдиката начислен жирный куш:\n"
            "• Выжившей мафии: *300* монет\n"
            "• Погибшим соратникам: *150* монет\n\n"
            "Город погружается во тьму... 🌃",
            parse_mode="Markdown",
        )
        return True

    return False
