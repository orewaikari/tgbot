import os


def load_dotenv():
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(dotenv_path):
        return
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

_raw_admins = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(p.strip()) for p in _raw_admins.split(",") if p.strip().isdigit()]


def is_superadmin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


if not BOT_TOKEN:
    print("Warning: BOT_TOKEN is not set. Create tgbot/.env or export BOT_TOKEN.")
