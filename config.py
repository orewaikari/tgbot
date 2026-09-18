import os
import sys


def run_setup_wizard():
    print("\n==================================================")
    print("🤖 НАСТРОЙКА ТЕЛЕГРАМ-БОТА (УСТАНОВКА НА СЕРВЕР) 🤖")
    print("==================================================\n")

    bot_token = ""
    while not bot_token:
        bot_token = input("🔑 Введите BOT_TOKEN от @BotFather: ").strip()
        if not bot_token:
            print("❌ Токен бота не может быть пустым!")

    admin_ids = input("👑 Введите ID администраторов через запятую (например, 123456789,987654321) [Enter для пропуска]: ").strip()

    use_userbot = input("⚡ Хотите использовать Pyrogram Userbot для автодобора участников в базу? (y/n) [n]: ").strip().lower()

    api_id = ""
    api_hash = ""
    userbot_session = ""

    if use_userbot in ["y", "yes", "д", "да"]:
        print("\n⚙️ Настройка Pyrogram Userbot (данные можно получить на my.telegram.org):")
        while not api_id:
            api_id = input("🔹 Введите API_ID: ").strip()
        while not api_hash:
            api_hash = input("🔹 Введите API_HASH: ").strip()
        while not userbot_session:
            userbot_session = input("🔹 Введите USERBOT_SESSION (строка сессии): ").strip()

    # Записываем в .env
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(dotenv_path, "w", encoding="utf-8") as f:
        f.write(f"BOT_TOKEN={bot_token}\n")
        if admin_ids:
            f.write(f"ADMIN_IDS={admin_ids}\n")
        if api_id:
            f.write(f"API_ID={api_id}\n")
            f.write(f"API_HASH={api_hash}\n")
            f.write(f"USERBOT_SESSION={userbot_session}\n")

    print("\n✅ Настройка успешно завершена! Файл tgbot/.env создан.")
    print("==================================================\n")

    # Сразу загружаем новые переменные в окружение
    os.environ["BOT_TOKEN"] = bot_token
    if admin_ids:
        os.environ["ADMIN_IDS"] = admin_ids
    if api_id:
        os.environ["API_ID"] = api_id
        os.environ["API_HASH"] = api_hash
        os.environ["USERBOT_SESSION"] = userbot_session


def load_dotenv():
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(dotenv_path):
        return False
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"').strip("'")
    return True


# Если файла настроек нет или он пуст, запускаем интерактивный мастер установки
dotenv_exists = load_dotenv()
if not dotenv_exists or not os.environ.get("BOT_TOKEN"):
    # Запускаем только в интерактивном режиме (tty)
    if sys.stdin.isatty():
        run_setup_wizard()
    else:
        print("Warning: .env is missing and stdin is not a tty. Interactive setup skipped.")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

API_ID = os.environ.get("API_ID", "")
API_HASH = os.environ.get("API_HASH", "")
USERBOT_SESSION = os.environ.get("USERBOT_SESSION", "")

_raw_admins = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(p.strip()) for p in _raw_admins.split(",") if p.strip().isdigit()]


def is_superadmin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


if not BOT_TOKEN:
    print("Warning: BOT_TOKEN is not set. Create tgbot/.env or export BOT_TOKEN.")
