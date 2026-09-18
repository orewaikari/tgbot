import asyncio
import random
from datetime import datetime, timedelta

from aiogram import F, Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import tgbot.database as db
import tgbot.utils as utils

router = Router()

TEA_VARIETIES = [
    "зеленый молочный улун",
    "китайский да хун пао",
    "индийский ассам с чабрецом",
    "травяной горный сбор с мятой",
    "японский пуэр многолетней выдержки",
    "нежный клубничный матча-латте",
    "ароматный бергамотовый эрл грей",
    "сладкий фруктовый каркаде",
    "успокаивающий ромашковый чай с медом",
    "элитный белый чай серебряные иглы",
]

COZY_TEA_MESSAGES = [
    "Ммм, какая теплота и уют! Душа наполняется гармонией. 😌",
    "Чувствуется прилив бодрости и вдохновения! Пора творить великие дела! 🚀",
    "Теплый пар согревает лицо, а тонкий аромат переносит в весенний сад. 🌸",
    "Каждый глоток приближает дзен. Жизнь определенно прекрасна! 🧸",
    "Вкус потрясающий! Усталость как рукой сняло. Можно и поболтать! 💬",
    "Чай получился невероятно крепким и насыщенным. Полный заряд энергии! ⚡️",
]

ANECDOTES = [
    "— Папа, а почему солнце встаёт на востоке, а заходит на западе?\n— Сынок, работает — не трогай! 💻",
    "Разговаривают два программиста:\n— Слышал, у тебя сын родился? Как назвал?\n— Да просто, С++.\n— А почему не Си?\n— Да Си — это прошлый век, а С++ имеет хорошую наследуемость! 👶",
    "В мире существует 10 типов людей: те, кто понимает двоичную систему счисления, и те, кто её не понимает. 🤖",
    "Заказчик на встрече:\n— Я хочу, чтобы приложение было быстрым, надёжным, красивым и дешёвым.\nПрограммист:\n— Отлично, выберите любые два пункта! 🎭",
    "Собрались как-то дизайнер, менеджер проекта и программист ехать в машине. Машина заглохла.\nМенеджер: «Давайте выйдем и зайдем обратно, вдруг заработает!»\nДизайнер: «Нет, давайте покрасим ее в красный цвет, так будет красивее!»\nПрограммист: «Так, давайте откроем все окна и закроем обратно, может поможет?» 🚗",
    "Программист ставит на тумбочку перед сном два стакана:\nОдин с водой — на случай, если захочет пить.\nВторой пустой — на случай, если не захочет. 🥛",
    "— Алло, это техподдержка?\n— Да, что у вас случилось?\n— Мой принтер начал печатать картинки с какими-то заговорами и пентаграммами!\n— О, у вас просто слетели шрифты, переустановите драйвер. Но на всякий случай окропите принтер святой водой! 🖨",
]

QUIZ_QUESTIONS = [
    {
        "q": "Какое ключевое слово используется для объявления асинхронных функций в Python?",
        "options": ["async", "await", "thread", "sync"],
        "correct": 0,
        "reward": 80,
    },
    {
        "q": "Какой протокол использует Telegram для шифрования сообщений?",
        "options": ["HTTPS", "MTProto", "SSH", "SSL"],
        "correct": 1,
        "reward": 100,
    },
    {
        "q": "Как звали первого программиста в истории?",
        "options": ["Алан Тьюринг", "Ада Лавлейс", "Билл Гейтс", "Грейс Хоппер"],
        "correct": 1,
        "reward": 120,
    },
    {
        "q": "В каком году вышел первый релиз Python?",
        "options": ["1991", "1995", "2000", "1989"],
        "correct": 0,
        "reward": 150,
    },
    {
        "q": "Что из этого НЕ является базовым типом данных в Python?",
        "options": ["list", "tuple", "dict", "array"],
        "correct": 3,
        "reward": 90,
    },
]

RP_ACTIONS = {
    "обнять": ("обнял(а)", "🤗"),
    "поцеловать": ("поцеловал(а)", "💋"),
    "погладить": ("погладил(а) по голове", "🐱"),
    "укусить": ("укусил(а) за ушко", "🦷"),
    "ударить": ("ударил(а) шпажкой", "💥"),
    "подарить цветы": ("подарил(а) шикарный букет цветов", "💐"),
}

ACTIVE_QUIZZES = {}


def escape_markdown(text: str) -> str:
    if not text:
        return ""
    return text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")


@router.message(
    F.text.lower().in_([
        "кошелек", "баланс", "мой баланс",
        "!кошелек", "!баланс", "!мой баланс",
        "/кошелек", "/баланс", "/мой баланс",
        "/wallet", "/balance", "wallet", "balance",
    ])
)
async def show_wallet(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_db = await db.get_user(user_id, chat_id)
    nickname = user_db["nickname"] if user_db and user_db["nickname"] else message.from_user.full_name
    coins = user_db["coins"] if user_db and user_db["coins"] is not None else 0
    sugar = user_db["sugar"] if user_db and user_db["sugar"] is not None else 0
    tea = user_db["tea_count"] if user_db and user_db["tea_count"] is not None else 0
    is_owner = user_id in [5026834657, 8002165201]
    coins_display = "∞" if is_owner else str(coins)
    await message.reply(
        f"💳 *Кошелёк {nickname}:*\n\n"
        f"🪙 Золотые монеты: *{coins_display}* \n"
        f"🍬 Кусочки сахара: *{sugar}* шт\n"
        f"🎒 Заварка чая: *{tea}* г\n\n"
        f"_Пишите сообщения, чтобы получать монеты, или играйте в `!казино`!_ 💰",
        parse_mode="Markdown",
    )


@router.message(
    F.text.lower().in_([
        "бонус", "получить бонус",
        "!бонус", "!получить бонус",
        "/бонус", "/получить бонус",
        "/bonus", "bonus",
    ])
)
async def claim_bonus_cmd(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    user_db = await db.get_user(user_id, chat_id)
    nickname = user_db["nickname"] if user_db and user_db["nickname"] else message.from_user.full_name

    amount = random.randint(150, 450)
    success, claimed, current_coins, remaining_sec = await db.claim_daily_bonus(user_id, chat_id, amount)

    if not success:
        hours = int(remaining_sec // 3600)
        minutes = int((remaining_sec % 3600) // 60)
        time_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
        await message.reply(
            f"⏱ Вы уже получали ежедневный бонус! Следующий доступен через *{time_str}*.",
            parse_mode="Markdown",
        )
        return

    await message.reply(
        f"🎁 *{nickname}*, вы получили ежедневный бонус!\n"
        f"🪙 На ваш счет начислено: *{claimed}* монет.\n"
        f"💳 Баланс: *{current_coins}* монет. 🎉",
        parse_mode="Markdown",
    )


@router.message(
    F.text.lower().in_([
        "магазин", "шоп",
        "!магазин", "!шоп",
        "/магазин", "/шоп",
        "/shop", "shop",
    ])
)
async def show_shop(message: Message):
    text = (
        "🛍 *КОМНАТНЫЙ ЧАЙНЫЙ МАГАЗИНЧИК* 🛍\n\n"
        "Здесь вы можете потратить свои золотые монеты:\n\n"
        "1. 🍵 *Чайный мешочек (50 г заварки)* — `200` монет\n"
        "   👉 Чтобы купить, напишите: `купить чай`\n\n"
        "2. 🍬 *Рафинад (1 кусочек сахара)* — `50` монет\n"
        "   👉 Чтобы купить, напишите: `купить сахар`\n\n"
        "3. 🏷 *Персональная роль (custom title)* — `25000` монет\n"
        "   👉 Чтобы купить, напишите: `купить тег [название]`\n\n"
        "🎒 _Сахарок можно использовать для чаепития командой `попить чай с сахаром`, что даст дополнительный XP любви в вашем браке!_"
    )
    await message.reply(text, parse_mode="Markdown")


@router.message(
    F.text.lower().startswith("купить")
    | F.text.lower().startswith("!купить")
    | F.text.lower().startswith("/купить")
)
async def buy_item(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.lower()
    user_db = await db.get_user(user_id, chat_id)
    coins = user_db["coins"] if user_db and user_db["coins"] is not None else 0
    nickname = user_db["nickname"] if user_db and user_db["nickname"] else message.from_user.full_name
    is_owner = user_id in [5026834657, 8002165201]

    if "чай" in text:
        price = 200
        if not is_owner and coins < price:
            await message.reply(f"❌ Недостаточно монет! Мешочек чая стоит {price} монет (у вас {coins}).")
            return
        if not is_owner:
            await db.add_coins(user_id, chat_id, -price)
        await db.farm_tea(user_id, chat_id, 50, "Купленный чай")
        await message.reply(f"✅ *{nickname}*, вы успешно купили мешочек чая (50 г) за {price} монет! 🍵", parse_mode="Markdown")
    elif "сахар" in text or "сахарок" in text:
        qty = 1
        args = text.split()
        for arg in args:
            if arg.isdigit():
                qty = int(arg)
                break
        if qty <= 0:
            qty = 1
        price = 50 * qty
        if not is_owner and coins < price:
            await message.reply(f"❌ Недостаточно монет! {qty} шт сахара стоит {price} монет (у вас {coins}).")
            return
        if not is_owner:
            await db.add_coins(user_id, chat_id, -price)
        await db.add_sugar(user_id, chat_id, qty)
        await message.reply(f"✅ *{nickname}*, вы успешно купили *{qty}* шт сахара за {price} монет! 🍬", parse_mode="Markdown")
    elif "тег" in text or "роль" in text:
        price = 25000
        if not is_owner and coins < price:
            await message.reply(f"❌ Недостаточно монет! Покупка персональной роли стоит {price} монет (у вас {coins}).")
            return

        parts = message.text.split(maxsplit=2)
        if len(parts) < 3 or not parts[2].strip():
            await message.reply("❌ Пожалуйста, напишите название роли после команды! Пример:\n`купить тег Чайный Магнат`")
            return
        new_title = parts[2].strip()
        if len(new_title) > 24:
            await message.reply("❌ Название роли слишком длинное (максимум 24 символа)!")
            return
        if not is_owner:
            await db.add_coins(user_id, chat_id, -price)
        await db.update_user_title(user_id, chat_id, new_title)

        tg_status = ""
        if await utils.apply_telegram_membertag(message.bot, chat_id, user_id, new_title):
            tg_status = " и успешно установили её как титул в Telegram!"
        else:
            tg_status = "! Роль сохранена в вашей анкете (установить её как тег в Telegram не удалось, возможно, у бота нет прав администратора)."
        await message.reply(f"✅ *{nickname}*, вы купили роль *{new_title}* за {price} монет{tg_status} 🎉", parse_mode="Markdown")
    else:
        await message.reply("❌ Неизвестный товар. Загляните в `магазин`!")


@router.message(
    F.text.lower().in_([
        "попить чай с сахаром", "выпить чай с сахаром", "пить чай с сахаром", "чай с сахаром",
        "!попить чай с сахаром", "!выпить чай с сахаром", "!пить чай с сахаром", "!чай с сахаром",
        "/попить чай с сахаром", "/выпить чай с сахаром", "/пить чай с сахаром", "/чай с сахаром",
    ])
)
async def drink_tea_with_sugar(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    user_db = await db.get_user(user_id, chat_id)
    nickname = user_db["nickname"] if user_db and user_db["nickname"] else message.from_user.full_name
    sugar = user_db["sugar"] if user_db and user_db["sugar"] is not None else 0
    tea = user_db["tea_count"] if user_db and user_db["tea_count"] is not None else 0

    if tea <= 0:
        await message.reply("❌ У вас закончились чайные запасы! Напишите `заварить чай`, чтобы пополнить мешочек. 🥺")
        return

    if sugar <= 0:
        await message.reply("❌ У вас нет сахара! Вы можете купить его в магазине (`купить сахар`) или попить обычный чай командой `попить чай`.")
        return

    res = await db.drink_tea(user_id, chat_id, use_sugar=True)
    success, current_tea, current_sugar, remaining_sec = res
    if not success:
        if remaining_sec > 0:
            minutes = int(remaining_sec // 60)
            seconds = int(remaining_sec % 60)
            time_str = f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
            await message.reply(f"⏱ Чашка еще слишком горячая! Вы сможете попить чаю через *{time_str}*.", parse_mode="Markdown")
        else:
            await message.reply("❌ Произошла ошибка при приготовлении сладкого чая.")
        return

    marriage_text = ""
    marriage = await db.get_user_marriage(user_id, chat_id)
    if marriage:
        _, love_level, _ = await db.care_marriage(marriage["id"], bonus_xp=3)
        partner_id = marriage["user2_id"] if marriage["user1_id"] == user_id else marriage["user1_id"]
        partner_db = await db.get_user(partner_id, chat_id)
        partner_name = partner_db["nickname"] if partner_db else f"Пользователь {partner_id}"
        marriage_text = f"\n💖 Вы попили чаю, думая о *{partner_name}*! Уровень любви в вашем браке увеличился до *{love_level}* XP! 🥰"

    await message.reply(
        f"🍬☕️ *{nickname}* налил(а) себе чашечку свежего чая, бросил(а) туда кубик рафинада и сладко выпил(а).\n"
        f"✨ Вкус невероятный, сладкий и безумно нежный! Усталость мгновенно исчезла! 🧸{marriage_text}\n"
        f"🎒 Осталось: *{current_tea}* г чая | *{current_sugar}* шт сахара.",
        parse_mode="Markdown",
    )


@router.message(F.text.lower().startswith("!роль") | F.text.lower().startswith("/role"))
async def set_custom_role_title(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    allowed = await utils.check_permission(message.bot, message.chat.id, message.from_user.id, "!роль", "administrator")
    if not allowed:
        await message.reply("❌ У вас нет прав администратора для назначения ролей!")
        return

    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ Укажите пользователя (ответом на сообщение или упомянув @username)!")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        parts_reply = message.text.split(maxsplit=1)
        if len(parts_reply) < 2:
            await message.reply("❌ Пожалуйста, напишите название роли! Пример:\n`!роль @username Чайный Мастер` или ответом `!роль Чайный Мастер`")
            return
        role_name = parts_reply[1].strip()
    else:
        role_name = parts[2].strip()

    if len(role_name) > 32:
        await message.reply("❌ Название роли слишком длинное (максимум 32 символа)!")
        return

    await db.update_user_title(target_id, message.chat.id, role_name)
    await message.reply(f"👑 Для *{target_name}* успешно установлена роль: *{role_name}*! Она будет отображаться в анкете.", parse_mode="Markdown")


@router.message(
    F.text.lower().startswith("!казино")
    | F.text.lower().startswith("!слоты")
    | F.text.lower().startswith("казино")
    | F.text.lower().startswith("слоты")
    | F.text.lower().startswith("/казино")
    | F.text.lower().startswith("/слоты")
)
async def slots_game(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    args = message.text.split()
    bet = 50
    if len(args) > 1 and args[1].isdigit():
        bet = int(args[1])
    if bet <= 0:
        await message.reply("❌ Ставка должна быть больше нуля монет!")
        return

    user_db = await db.get_user(user_id, chat_id)
    coins = user_db["coins"] if user_db and user_db["coins"] is not None else 0
    nickname = user_db["nickname"] if user_db and user_db["nickname"] else message.from_user.full_name
    is_owner = user_id in [5026834657, 8002165201]

    if not is_owner and coins < bet:
        await message.reply(f"❌ Недостаточно монет для ставки! У вас в кошельке всего {coins} монет.")
        return

    if not is_owner:
        await db.add_coins(user_id, chat_id, -bet)

    dice_msg = await message.answer_dice(emoji="🎰")
    val = dice_msg.dice.value

    await asyncio.sleep(2.0)

    if val == 64:
        win_amount = bet * 15
        new_balance = await db.add_coins(user_id, chat_id, win_amount)
        await message.reply(
            f"🎰🎰🎰 *ДЖЕКПОТ!!!* 🎰🎰🎰\n\n"
            f"🎉 *{nickname}*, выбили ТРИ СЕМЁРКИ (777)!\n"
            f"💰 Вы выиграли суперприз: *{win_amount}* монет! 🏆\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )
    elif val in [1, 22, 43]:
        win_amount = bet * 8
        new_balance = await db.add_coins(user_id, chat_id, win_amount)
        await message.reply(
            f"🍒🍇🍋 *Тройное совпадение!* 🍇🍒🍋\n\n"
            f"🎉 *{nickname}*, у вас совпали три символа! \n"
            f"💰 Вы выиграли: *{win_amount}* монет! 🥳\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )
    elif val in [4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60]:
        win_amount = bet * 2
        new_balance = await db.add_coins(user_id, chat_id, win_amount)
        await message.reply(
            f"🍒 *Частичный выигрыш!* 🍒\n\n"
            f"🎉 *{nickname}*, выпали два одинаковых символа! \n"
            f"💰 Вы вернули ставку и выиграли: *{win_amount}* монет!\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )
    else:
        user_db = await db.get_user(user_id, chat_id)
        new_balance = user_db["coins"] if user_db else 0
        await message.reply(
            f"😢 *{nickname}*, увы, совпадений нет! Вы проиграли *{bet}* монет.\n"
            f"🔮 Попробуйте снова, удача обязательно улыбнется!\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )


@router.message(
    F.text.lower().startswith("!дартс")
    | F.text.lower().startswith("дартс")
    | F.text.lower().startswith("/дартс")
)
async def darts_game(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    bet = 50
    if len(args) > 1 and args[1].isdigit():
        bet = int(args[1])
    if bet <= 0:
        await message.reply("❌ Ставка должна быть больше нуля монет!")
        return

    user_db = await db.get_user(user_id, chat_id)
    coins = user_db["coins"] if user_db and user_db["coins"] is not None else 0
    nickname = user_db["nickname"] if user_db and user_db["nickname"] else message.from_user.full_name
    is_owner = user_id in [5026834657, 8002165201]

    if not is_owner and coins < bet:
        await message.reply(f"❌ Недостаточно монет для ставки! У вас в кошельке всего {coins} монет.")
        return
    if not is_owner:
        await db.add_coins(user_id, chat_id, -bet)

    dice_msg = await message.answer_dice(emoji="🎯")
    val = dice_msg.dice.value
    await asyncio.sleep(2.0)

    if val == 6:
        win_amount = bet * 4
        new_balance = await db.add_coins(user_id, chat_id, win_amount)
        await message.reply(
            f"🎯 *ПРЯМО В ЯБЛОЧКО!!!* 🎯\n\n"
            f"🎉 *{nickname}*, вы попали в самый центр мишени!\n"
            f"💰 Выигрыш: *{win_amount}* монет! 🏆\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )
    elif val in [4, 5]:
        win_amount = int(bet * 1.5)
        new_balance = await db.add_coins(user_id, chat_id, win_amount)
        await message.reply(
            f"🎯 *Хороший бросок!* 🎯\n\n"
            f"🎉 *{nickname}*, вы попали во внутренние кольца мишени!\n"
            f"💰 Выигрыш: *{win_amount}* монет! 🥳\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )
    else:
        user_db = await db.get_user(user_id, chat_id)
        new_balance = user_db["coins"] if user_db else 0
        await message.reply(
            f"💨 *Промах!* 🎯\n\n"
            f"📉 *{nickname}*, дротик улетел в молоко или мимо! Вы проиграли *{bet}* монет.\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )


@router.message(
    F.text.lower().startswith("!боулинг")
    | F.text.lower().startswith("боулинг")
    | F.text.lower().startswith("/боулинг")
)
async def bowling_game(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    bet = 50
    if len(args) > 1 and args[1].isdigit():
        bet = int(args[1])
    if bet <= 0:
        await message.reply("❌ Ставка должна быть больше нуля монет!")
        return

    user_db = await db.get_user(user_id, chat_id)
    coins = user_db["coins"] if user_db and user_db["coins"] is not None else 0
    nickname = user_db["nickname"] if user_db and user_db["nickname"] else message.from_user.full_name
    is_owner = user_id in [5026834657, 8002165201]

    if not is_owner and coins < bet:
        await message.reply(f"❌ Недостаточно монет для ставки! У вас в кошельке всего {coins} монет.")
        return
    if not is_owner:
        await db.add_coins(user_id, chat_id, -bet)

    dice_msg = await message.answer_dice(emoji="🎳")
    val = dice_msg.dice.value
    await asyncio.sleep(2.0)

    if val == 6:
        win_amount = bet * 4
        new_balance = await db.add_coins(user_id, chat_id, win_amount)
        await message.reply(
            f"🎳 *СТРАЙК!!!* 🎳\n\n"
            f"🎉 *{nickname}*, вы сбили абсолютно все кегли одним ударом!\n"
            f"💰 Выигрыш: *{win_amount}* монет! 🏆\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )
    elif val in [3, 4, 5]:
        win_amount = int(bet * 1.5)
        new_balance = await db.add_coins(user_id, chat_id, win_amount)
        await message.reply(
            f"🎳 *Отличный удар!* 🎳\n\n"
            f"🎉 *{nickname}*, вы сбили {val} кеглей!\n"
            f"💰 Выигрыш: *{win_amount}* монет! 🥳\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )
    else:
        user_db = await db.get_user(user_id, chat_id)
        new_balance = user_db["coins"] if user_db else 0
        await message.reply(
            f"🧹 *Шар улетел в желоб!* 🎳\n\n"
            f"📉 *{nickname}*, вы сбили всего {val} кеглей. Вы проиграли *{bet}* монет.\n"
            f"💳 Баланс: *{new_balance}* монет.",
            parse_mode="Markdown",
        )


@router.message(
    F.text.lower().in_([
        "!анекдот", "анекдот", "/anecdote", "расскажи анекдот",
        "/анекдот", "!расскажи анекдот", "/расскажи анекдот", "anecdote",
    ])
)
async def tell_anecdote(message: Message):
    anecdote = random.choice(ANECDOTES)
    await message.reply(f"😂 *Лови анекдот:* \n\n{anecdote}", parse_mode="Markdown")


@router.message(
    F.text.lower().in_([
        "!викторина", "викторина", "/quiz", "запустить викторину",
        "/викторина", "!запустить викторину", "/запустить викторину", "quiz",
    ])
)
async def start_quiz(message: Message):
    chat_id = message.chat.id

    if chat_id in ACTIVE_QUIZZES:
        await message.reply("⚠️ В этом чате уже запущена активная викторина! Ответьте на неё, прежде чем запускать новую.")
        return

    quiz = random.choice(QUIZ_QUESTIONS)
    correct_idx = quiz["correct"]
    reward = quiz["reward"]

    keyboard_buttons = []
    for i, opt in enumerate(quiz["options"]):
        is_correct = 1 if i == correct_idx else 0
        keyboard_buttons.append([InlineKeyboardButton(text=opt, callback_data=f"quiz:{is_correct}:{reward}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    ACTIVE_QUIZZES[chat_id] = True

    await message.reply(
        f"🧠 *ИНТЕЛЛЕКТУАЛЬНАЯ ВИКТОРИНА!* 🧠\n\n"
        f"❓ *Вопрос:* {quiz['q']}\n\n"
        f"🪙 *Награда за правильный ответ:* {reward} монет!\n"
        f"_Первый ответивший правильно забирает всю награду! Поехали!_",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("quiz:"))
async def answer_quiz(callback: CallbackQuery):
    chat_id = callback.message.chat.id

    if chat_id not in ACTIVE_QUIZZES:
        await callback.answer("⏳ Эта викторина уже завершилась!", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    parts = callback.data.split(":")
    is_correct = int(parts[1])
    reward = int(parts[2])

    user_id = callback.from_user.id
    nickname = callback.from_user.full_name
    user_db = await db.get_user(user_id, chat_id)
    if user_db and user_db["nickname"]:
        nickname = user_db["nickname"]

    if is_correct:
        ACTIVE_QUIZZES.pop(chat_id, None)
        new_balance = await db.add_coins(user_id, chat_id, reward)

        await callback.message.edit_text(
            f"🧠 *ИНТЕЛЛЕКТУАЛЬНАЯ ВИКТОРИНА!* 🧠\n\n"
            f"❓ {callback.message.text.split('❓ ')[1].split('🪙 ')[0].strip()}\n\n"
            f"🏆 *Победитель:* {nickname} ответил(а) абсолютно верно!\n"
            f"💰 *Выигрыш:* {reward} монет начислены на баланс! 🎉\n"
            f"💳 Новый баланс: {new_balance} монет.",
            reply_markup=None,
            parse_mode="Markdown",
        )
        await callback.answer("🎉 Абсолютно верно! Монеты зачислены на счет!", show_alert=True)
    else:
        await callback.answer("❌ Неверно! Попробуйте еще раз или дайте шанс другим!", show_alert=True)


@router.message(F.text.lower().in_(["заварить чай", "заварка", "!заварить", "/tea_brew"]))
async def brew_tea(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    sender_name = message.from_user.full_name

    user_db = await db.get_user(user_id, chat_id)
    if user_db and user_db["nickname"]:
        sender_name = user_db["nickname"]

    amount = random.randint(5, 25)
    tea_variety = random.choice(TEA_VARIETIES)

    success, current_tea, remaining_sec, _ = await db.farm_tea(user_id, chat_id, amount, tea_variety)

    if not success:
        minutes = int(remaining_sec // 60)
        seconds = int(remaining_sec % 60)
        time_str = f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
        await message.reply(f"⏱ Чайник еще не остыл! Вы сможете заварить новый чай через *{time_str}*.", parse_mode="Markdown")
        return

    await message.reply(
        f"🍵 *{sender_name}* заварил(а) вкуснейший *{tea_variety}* и получил(а) *{amount}* г заварки!\n"
        f"🎒 Теперь у вас в запасе: *{current_tea}* г чая! ✨",
        parse_mode="Markdown",
    )


@router.message(F.text.lower().in_(["попить чай", "выпить чай", "пить чай", "!попить", "/tea_drink"]))
async def drink_tea_cmd(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    sender_name = message.from_user.full_name
    user_db = await db.get_user(user_id, chat_id)
    if user_db and user_db["nickname"]:
        sender_name = user_db["nickname"]
    res = await db.drink_tea(user_id, chat_id, use_sugar=False)
    success, current_tea, _, remaining_sec = res
    if not success:
        if remaining_sec > 0:
            minutes = int(remaining_sec // 60)
            seconds = int(remaining_sec % 60)
            time_str = f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
            await message.reply(f"⏱ Чашка еще слишком горячая! Вы сможете попить чаю через *{time_str}*.", parse_mode="Markdown")
        else:
            await message.reply("❌ У вас закончились чайные запасы! Напишите `заварить чай`, чтобы пополнить мешочек. 🥺")
        return
    cozy_msg = random.choice(COZY_TEA_MESSAGES)
    await message.reply(
        f"☕️ *{sender_name}* налил(а) себе чашечку свежего чая и с удовольствием выпил(а) её.\n"
        f"✨ {cozy_msg}\n"
        f"🎒 В запасе осталось: *{current_tea}* г чая.",
        parse_mode="Markdown",
    )


@router.message(F.text.lower().in_(["мой чай", "чай", "баланс чая", "!чай", "/tea"]))
async def show_tea_balance(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    sender_name = message.from_user.full_name
    user_db = await db.get_user(user_id, chat_id)
    if user_db:
        if user_db["nickname"]:
            sender_name = user_db["nickname"]
        tea_count = user_db["tea_count"]
        tea_drank = user_db["tea_drank"] if user_db["tea_drank"] is not None else 0
    else:
        tea_count = 0
        tea_drank = 0

    await message.reply(
        f"🍵 *Чайная полка {sender_name}:*\n\n"
        f"🎒 Заварки в мешочке: *{tea_count}* г чая\n"
        f"☕️ Всего выпито чашек: *{tea_drank}*\n\n"
        f"_Используйте команды `заварить чай` и `попить чай`_ 🧸",
        parse_mode="Markdown",
    )


@router.message(F.text.lower().startswith("угостить чаем") | F.text.lower().startswith("/tea_gift"))
async def gift_tea_cmd(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Эту команду можно использовать только в группах!")
        return

    args = message.text.split()
    amount = 5

    for arg in args:
        if arg.isdigit():
            amount = int(arg)
            break

    if amount <= 0:
        await message.reply("❌ Количество чая должно быть больше нуля!")
        return

    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ Укажите, кого хотите угостить чаем (ответом на сообщение или упомянув @username)!")
        return

    if target_id == message.from_user.id:
        await message.reply("❌ Вы не можете угостить чаем самого себя!")
        return

    sender_name = message.from_user.full_name
    sender_db = await db.get_user(message.from_user.id, message.chat.id)
    if sender_db and sender_db["nickname"]:
        sender_name = sender_db["nickname"]

    success = await db.gift_tea(message.from_user.id, target_id, message.chat.id, amount)

    if not success:
        sender_tea = sender_db["tea_count"] if sender_db else 0
        await message.reply(f"❌ У вас недостаточно заварки! Доступно всего *{sender_tea}* г.", parse_mode="Markdown")
        return

    await message.reply(
        f"🎁 *{sender_name}* щедро угостил(а) *{target_name}* ароматным чаем (*{amount}* г)!\n"
        f"Как же это мило и тепло! 🥰",
        parse_mode="Markdown",
    )


@router.message(F.text.lower().startswith("брак") | F.text.lower().startswith("!брак") | F.text.lower().startswith("/брак"))
async def propose_marriage(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Браки заключаются только в чатах!")
        return
    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        await message.reply("❌ Укажите, с кем хотите заключить брак (ответом на сообщение или упомянув @username)!")
        return
    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя заключить брак с самим собой!")
        return
    sender_name = message.from_user.full_name
    sender_db = await db.get_user(message.from_user.id, message.chat.id)
    if sender_db and sender_db["nickname"]:
        sender_name = sender_db["nickname"]

    m1 = await db.get_user_marriage(message.from_user.id, message.chat.id)
    if m1:
        await message.reply("❌ Вы уже состоите в браке! Сначала оформите `развод`.")
        return

    m2 = await db.get_user_marriage(target_id, message.chat.id)
    if m2:
        await message.reply(f"❌ *{target_name}* уже состоит в браке с другим человеком!", parse_mode="Markdown")
        return
    success = await db.create_proposal(message.chat.id, message.from_user.id, target_id)
    if not success:
        await message.reply("❌ Не удалось отправить предложение (один из вас может быть уже помолвлен).")
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔹 Согласиться", callback_data=f"mrg_accept:{message.from_user.id}:{target_id}"),
                InlineKeyboardButton(text="🔹 Отклонить", callback_data=f"mrg_decline:{message.from_user.id}:{target_id}"),
            ]
        ]
    )
    await message.reply(
        f"💍 *{target_name}*, внимание!\n\n"
        f"💖 *{sender_name}* делает вам предложение руки и сердца и предлагает вступить в брак!\n\n"
        f"💬 Нажмите на одну из кнопок ниже, чтобы сделать свой выбор! 💕",
        reply_markup=markup,
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("mrg_accept:"))
async def accept_marriage_callback(callback_query: CallbackQuery):
    data = callback_query.data.split(":")
    proposer_id = int(data[1])
    target_id = int(data[2])
    chat_id = callback_query.message.chat.id
    if callback_query.from_user.id != target_id:
        await callback_query.answer("❌ Это предложение адресовано не вам!", show_alert=True)
        return
    success = await db.accept_marriage(chat_id, proposer_id, target_id)
    if not success:
        success = await db.accept_marriage(chat_id, target_id, proposer_id)
    if not success:
        await callback_query.answer("❌ Срок действия предложения истек или оно не существует.", show_alert=True)
        await callback_query.message.edit_text("❌ Предложение брака более недействительно.")
        return
    await callback_query.answer("Поздравляем со вступлением в брак! 🎉")
    p_db = await db.get_user(proposer_id, chat_id)
    t_db = await db.get_user(target_id, chat_id)
    p_name = escape_markdown(p_db["nickname"] if p_db else f"ID {proposer_id}")
    t_name = escape_markdown(t_db["nickname"] if t_db else f"ID {target_id}")
    await callback_query.message.edit_text(
        f"🎉 *ОФИЦИАЛЬНОЕ СВИДЕТЕЛЬСТВО О БРАКЕ* 🎉\n\n"
        f"💖 Сегодня сердца *{p_name}* и *{t_name}* соединились навек!\n"
        f"✨ Поздравляем новобрачных! Объявляем вас мужем и женой! 💍\n\n"
        f"🗺 Теперь вы можете заботиться о браке командой `!забота`!",
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("mrg_decline:"))
async def decline_marriage_callback(callback_query: CallbackQuery):
    data = callback_query.data.split(":")
    proposer_id = int(data[1])
    target_id = int(data[2])
    chat_id = callback_query.message.chat.id
    if callback_query.from_user.id != target_id:
        await callback_query.answer("❌ Это предложение адресовано не вам!", show_alert=True)
        return
    await db.delete_proposal(chat_id, proposer_id, target_id)
    await callback_query.answer("Вы отклонили предложение.")
    p_db = await db.get_user(proposer_id, chat_id)
    t_db = await db.get_user(target_id, chat_id)
    p_name = escape_markdown(p_db["nickname"] if p_db else f"ID {proposer_id}")
    t_name = escape_markdown(t_db["nickname"] if t_db else f"ID {target_id}")
    await callback_query.message.edit_text(
        f"💔 *{t_name}* отклонил(а) предложение руки и сердца от *{p_name}*.",
        parse_mode="Markdown",
    )


@router.message(F.text.lower().in_(["развод", "!развод", "/развод", "/divorce"]))
async def divorce_cmd(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    marriage = await db.get_user_marriage(message.from_user.id, message.chat.id)
    if not marriage:
        await message.reply("❌ Вы не состоите в браке, разводиться не с кем!")
        return
    partner_id = marriage["user2_id"] if marriage["user1_id"] == message.from_user.id else marriage["user1_id"]
    partner_db = await db.get_user(partner_id, message.chat.id)
    partner_name = partner_db["nickname"] if partner_db else f"Пользователь {partner_id}"
    await db.divorce(message.from_user.id, message.chat.id)
    await message.reply(
        f"💔 С сожалением сообщаем, что брак между вами и *{partner_name}* официально расторгнут. "
        f"Желаем каждому найти свое счастье отдельно. 🥺",
        parse_mode="Markdown",
    )


@router.message(
    F.text.lower().in_([
        "!забота", "забота", "/забота", "/care",
        "!позаботиться", "позаботиться", "/позаботиться",
    ])
)
async def care_marriage_cmd(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    marriage = await db.get_user_marriage(message.from_user.id, message.chat.id)
    if not marriage:
        await message.reply("❌ Вы не состоите в браке! Отправьте предложение командой `брак [участник]`.")
        return
    success, love_level, remaining_sec = await db.care_marriage(marriage["id"])
    if not success:
        minutes = int(remaining_sec // 60)
        seconds = int(remaining_sec % 60)
        time_str = f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
        await message.reply(f"⏱ Вы уже проявляли заботу недавно! Попробуйте снова через *{time_str}*.", parse_mode="Markdown")
        return
    partner_id = marriage["user2_id"] if marriage["user1_id"] == message.from_user.id else marriage["user1_id"]
    partner_db = await db.get_user(partner_id, message.chat.id)
    partner_name = partner_db["nickname"] if partner_db else f"Пользователь {partner_id}"

    sender_name = message.from_user.full_name
    sender_db = await db.get_user(message.from_user.id, message.chat.id)
    if sender_db and sender_db["nickname"]:
        sender_name = sender_db["nickname"]

    await message.reply(
        f"🥰 *{sender_name}* проявил(а) нежную заботу об отношениях с *{partner_name}*!\n"
        f"💖 Уровень любви и понимания в вашем браке вырос до *{love_level}* XP! ❤️",
        parse_mode="Markdown",
    )


@router.message(lambda msg: msg.text and msg.text.lower().split()[0] in RP_ACTIONS)
async def handle_rp_action(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    action_cmd = message.text.lower().split()[0]
    action_verb, action_emoji = RP_ACTIONS[action_cmd]

    target_id, target_username, target_name = await utils.parse_target_user(message, message.bot)
    if not target_id:
        return

    sender_name = message.from_user.full_name
    sender_db = await db.get_user(message.from_user.id, message.chat.id)
    if sender_db and sender_db["nickname"]:
        sender_name = sender_db["nickname"]

    if target_id == message.from_user.id:
        await message.reply(f"🤔 {action_emoji} Вы пытаетесь сделать это с самим собой? Это выглядит забавно!")
        return

    await message.reply(f"{action_emoji} *{sender_name}* {action_verb} *{target_name}*!", parse_mode="Markdown")


async def parse_coins_command(message: Message, bot: Bot) -> tuple:
    text = message.text
    if not text:
        return None, None, None
    target_id, target_name, amount = None, None, None

    words = text.split()
    if len(words) < 2:
        return None, None, None

    if message.reply_to_message:
        tgt = message.reply_to_message.from_user
        if tgt:
            target_id = tgt.id
            target_name = tgt.full_name

            for w in words:
                if w.isdigit():
                    amount = int(w)
                    break
            return target_id, target_name, amount

    if len(words) >= 4:
        target_str = words[2]
        amount_str = words[3]
        if amount_str.isdigit():
            amount = int(amount_str)
        if target_str.startswith("@"):
            uname = target_str.replace("@", "").lower()
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, nickname, username FROM users WHERE chat_id = ? AND LOWER(username) = ?", (message.chat.id, uname))
            row = cursor.fetchone()
            conn.close()
            if row:
                target_id = row["user_id"]
                target_name = row["nickname"]
        elif target_str.isdigit():
            target_id = int(target_str)
            user_db = await db.get_user(target_id, message.chat.id)
            if user_db:
                target_name = user_db["nickname"] or user_db["username"]
            else:
                target_name = f"Пользователь {target_id}"
        if target_id and amount:
            return target_id, target_name, amount
    return None, None, None


@router.message(F.text.lower().startswith("выдать монеты") | F.text.lower().startswith("!выдать монеты") | F.text.lower().startswith("/выдать монеты"))
async def give_coins_cmd(message: Message):
    user_id = message.from_user.id
    if user_id not in [5026834657, 8002165201]:
        await message.reply("❌ Эта команда доступна только владельцам бота!")
        return
    target_id, target_name, amount = await parse_coins_command(message, message.bot)
    if not target_id:
        await message.reply("❌ Укажите пользователя (ответом на сообщение, упомянув @username или указав его ID) и количество монет!")
        return
    if amount is None or amount <= 0:
        await message.reply("❌ Укажите корректное количество монет для выдачи!")
        return
    new_bal = await db.add_coins(target_id, message.chat.id, amount)
    tgt_bal_display = "∞" if target_id in [5026834657, 8002165201] else str(new_bal)
    await message.reply(
        f"🪙 Владелец начислил *{amount}* монет пользователю *{target_name}*!\n"
        f"💳 Новый баланс: *{tgt_bal_display}* монет.",
        parse_mode="Markdown",
    )


@router.message(F.text.lower().startswith("забрать монеты") | F.text.lower().startswith("!забрать монеты") | F.text.lower().startswith("/забрать монеты"))
async def take_coins_cmd(message: Message):
    user_id = message.from_user.id
    if user_id not in [5026834657, 8002165201]:
        await message.reply("❌ Эта команда доступна только владельцам бота!")
        return
    target_id, target_name, amount = await parse_coins_command(message, message.bot)
    if not target_id:
        await message.reply("❌ Укажите пользователя (ответом на сообщение, упомянув @username или указав его ID) и количество монет!")
        return
    if amount is None or amount <= 0:
        await message.reply("❌ Укажите корректное количество монет для забирания!")
        return

    tgt_db = await db.get_user(target_id, message.chat.id)
    current_coins = tgt_db["coins"] if (tgt_db and tgt_db["coins"] is not None) else 0
    if amount > current_coins:
        amount = current_coins
    new_bal = await db.add_coins(target_id, message.chat.id, -amount)
    tgt_bal_display = "∞" if target_id in [5026834657, 8002165201] else str(new_bal)
    await message.reply(
        f"🪙 Владелец забрал *{amount}* монет у пользователя *{target_name}*!\n"
        f"💳 Новый баланс: *{tgt_bal_display}* монет.",
        parse_mode="Markdown",
    )
