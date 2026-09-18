import asyncio
import os
import re
import sqlite3
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        chat_id INTEGER PRIMARY KEY,
        rules TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER,
        chat_id INTEGER,
        username TEXT,
        nickname TEXT,
        description TEXT,
        admin_role TEXT DEFAULT 'member',
        custom_title TEXT,
        messages_day INTEGER DEFAULT 0,
        messages_week INTEGER DEFAULT 0,
        messages_month INTEGER DEFAULT 0,
        messages_total INTEGER DEFAULT 0,
        last_message_date TEXT,
        joined_date TEXT,
        tea_count INTEGER DEFAULT 0,
        tea_drank INTEGER DEFAULT 0,
        last_tea_farm TEXT,
        coins INTEGER DEFAULT 0,
        sugar INTEGER DEFAULT 0,
        last_daily_bonus TEXT,
        PRIMARY KEY (user_id, chat_id)
    )
    """)

    for col_def in [
        "coins INTEGER DEFAULT 0",
        "sugar INTEGER DEFAULT 0",
        "last_daily_bonus TEXT",
        "last_tea_drink TEXT",
        "photo TEXT",
        "rest_until TEXT",
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marriages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        user1_id INTEGER,
        user2_id INTEGER,
        marriage_date TEXT,
        love_level INTEGER DEFAULT 1,
        last_cared TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proposals (
        chat_id INTEGER,
        proposer_id INTEGER,
        target_id INTEGER,
        proposal_date TEXT,
        PRIMARY KEY (chat_id, proposer_id, target_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warns (
        chat_id INTEGER,
        user_id INTEGER,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (chat_id, user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS command_permissions (
        chat_id INTEGER,
        command TEXT,
        min_role TEXT,
        PRIMARY KEY (chat_id, command)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS whispers (
        whisper_id TEXT PRIMARY KEY,
        sender_id INTEGER,
        sender_name TEXT,
        target_username TEXT,
        message_text TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        class_name TEXT,
        status TEXT DEFAULT 'free',
        user_id INTEGER,
        user_name TEXT,
        UNIQUE(name, class_name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registration_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_registrations (
        user_id INTEGER PRIMARY KEY,
        character_name TEXT,
        timestamp TEXT
    )
    """)

    file_path = "/home/roland/mlbb_heroes_by_class.txt"
    if os.path.exists(file_path):
        header_map = {
            "ТАНКИ": "Танк",
            "БОЙЦЫ": "Боец",
            "УБИЙЦЫ": "Ассасин",
            "МАГИ": "Маг",
            "СТРЕЛКИ": "Стрелок",
            "ПОДДЕРЖКА": "Поддержка",
        }

        mlbb_heroes = []
        current_class = None
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                match = re.search(r"===\s*([А-Я]+)\s*\(\d+\)\s*===", line)
                if match:
                    current_class = header_map.get(match.group(1))
                    continue
                if current_class and line.startswith("-"):
                    hero_name = line.lstrip("- ").strip()
                    hero_name = re.sub(r"\s*\(.*?\)\s*", "", hero_name).strip()
                    if hero_name:
                        mlbb_heroes.append((hero_name, current_class))

        valid_set = set(mlbb_heroes)
        cursor.execute("SELECT name, class_name FROM characters")
        existing_rows = cursor.fetchall()
        for row in existing_rows:
            if (row["name"], row["class_name"]) not in valid_set:
                cursor.execute(
                    "DELETE FROM characters WHERE name = ? AND class_name = ?",
                    (row["name"], row["class_name"]),
                )

        cursor.executemany(
            "INSERT OR IGNORE INTO characters (name, class_name, status) VALUES (?, ?, 'free')",
            mlbb_heroes,
        )

        private_chat_id = _get_reg_setting("private_chat_id")
        if private_chat_id:
            try:
                p_id = int(private_chat_id)
                cursor.execute(
                    """
                INSERT OR IGNORE INTO users (user_id, chat_id, nickname, username, admin_role)
                VALUES (5026834657, ?, 'Арлотт', 'admin_arlott', 'owner')
                """,
                    (p_id,),
                )
                cursor.execute(
                    """
                INSERT OR IGNORE INTO users (user_id, chat_id, nickname, username, admin_role)
                VALUES (8002165201, ?, 'Лейла', 'admin_layla', 'owner')
                """,
                    (p_id,),
                )
            except ValueError:
                pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anonymous_appeals (
        admin_message_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rejected_users (
        user_id INTEGER PRIMARY KEY,
        rejected_at TEXT
    )
    """)
    conn.commit()
    conn.close()


async def run_query(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


def _log_message(user_id: int, chat_id: int, username: str, full_name: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    user = cursor.fetchone()

    now = datetime.now()
    now_str = now.isoformat()
    today_date = date.today()

    curr_day = today_date.day
    curr_week = today_date.isocalendar()[1]
    curr_month = today_date.month
    curr_year = today_date.year

    if not user:
        cursor.execute(
            """
        INSERT INTO users (user_id, chat_id, username, nickname, messages_day, messages_week, messages_month, messages_total, last_message_date, joined_date, coins)
        VALUES (?, ?, ?, ?, 1, 1, 1, 1, ?, ?, 100)
        """,
            (user_id, chat_id, username, full_name, now_str, now_str),
        )
    else:
        last_date_str = user["last_message_date"]

        msg_day = user["messages_day"]
        msg_week = user["messages_week"]
        msg_month = user["messages_month"]
        msg_total = user["messages_total"]
        current_coins = user["coins"] if user["coins"] is not None else 0

        if last_date_str:
            last_date = datetime.fromisoformat(last_date_str)
            last_day = last_date.day
            last_week = last_date.isocalendar()[1]
            last_month = last_date.month
            last_year = last_date.year

            if (
                curr_day != last_day
                or curr_month != last_month
                or curr_year != last_year
            ):
                msg_day = 0

            if curr_week != last_week or curr_year != last_year:
                msg_week = 0

            if curr_month != last_month or curr_year != last_year:
                msg_month = 0

        msg_day += 1
        msg_week += 1
        msg_month += 1
        msg_total += 1
        current_coins += 1

        cursor.execute(
            """
        UPDATE users
        SET username = ?, nickname = COALESCE(nickname, ?), messages_day = ?, messages_week = ?, messages_month = ?, messages_total = ?, last_message_date = ?, coins = ?
        WHERE user_id = ? AND chat_id = ?
        """,
            (
                username,
                full_name,
                msg_day,
                msg_week,
                msg_month,
                msg_total,
                now_str,
                current_coins,
                user_id,
                chat_id,
            ),
        )

    conn.commit()
    conn.close()


async def log_message(user_id: int, chat_id: int, username: str, full_name: str):
    await run_query(_log_message, user_id, chat_id, username, full_name)


def _migrate_chat_id(old_chat_id: int, new_chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    tables = [
        ("chats", "chat_id"),
        ("users", "chat_id"),
        ("marriages", "chat_id"),
        ("proposals", "chat_id"),
        ("warns", "chat_id"),
        ("command_permissions", "chat_id"),
    ]

    for table, col in tables:
        try:
            cursor.execute(
                f"UPDATE OR IGNORE {table} SET {col} = ? WHERE {col} = ?",
                (new_chat_id, old_chat_id),
            )
            cursor.execute(f"DELETE FROM {table} WHERE {col} = ?", (old_chat_id,))
        except sqlite3.Error:
            pass

    conn.commit()
    conn.close()


async def migrate_chat_id(old_chat_id: int, new_chat_id: int):
    await run_query(_migrate_chat_id, old_chat_id, new_chat_id)


def _get_user(user_id: int, chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


async def get_user(user_id: int, chat_id: int):
    return await run_query(_get_user, user_id, chat_id)


def _update_user_role(user_id: int, chat_id: int, role: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, chat_id, admin_role) VALUES (?, ?, ?) ON CONFLICT(user_id, chat_id) DO UPDATE SET admin_role = ?",
        (user_id, chat_id, role, role),
    )
    conn.commit()
    conn.close()


async def update_user_role(user_id: int, chat_id: int, role: str):
    await run_query(_update_user_role, user_id, chat_id, role)


def _update_user_title(user_id: int, chat_id: int, title: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, chat_id, custom_title) VALUES (?, ?, ?) ON CONFLICT(user_id, chat_id) DO UPDATE SET custom_title = ?",
        (user_id, chat_id, title, title),
    )
    conn.commit()
    conn.close()


async def update_user_title(user_id: int, chat_id: int, title: str):
    await run_query(_update_user_title, user_id, chat_id, title)


def _update_user_nickname(user_id: int, chat_id: int, nickname: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, chat_id, nickname) VALUES (?, ?, ?) ON CONFLICT(user_id, chat_id) DO UPDATE SET nickname = ?",
        (user_id, chat_id, nickname, nickname),
    )
    conn.commit()
    conn.close()


async def update_user_nickname(user_id: int, chat_id: int, nickname: str):
    await run_query(_update_user_nickname, user_id, chat_id, nickname)


def _update_user_description(user_id: int, chat_id: int, desc: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, chat_id, description) VALUES (?, ?, ?) ON CONFLICT(user_id, chat_id) DO UPDATE SET description = ?",
        (user_id, chat_id, desc, desc),
    )
    conn.commit()
    conn.close()


async def update_user_description(user_id: int, chat_id: int, desc: str):
    await run_query(_update_user_description, user_id, chat_id, desc)


def _set_user_rest(user_id: int, chat_id: int, rest_until_str: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, chat_id, rest_until) VALUES (?, ?, ?) ON CONFLICT(user_id, chat_id) DO UPDATE SET rest_until = ?",
        (user_id, chat_id, rest_until_str, rest_until_str),
    )
    conn.commit()
    conn.close()


async def set_user_rest(user_id: int, chat_id: int, rest_until_str: str):
    await run_query(_set_user_rest, user_id, chat_id, rest_until_str)


def _get_shared_chat_members(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT user_id, nickname, username, messages_total
    FROM users
    WHERE chat_id IN (
        SELECT chat_id FROM users WHERE user_id = ?
    )
    AND user_id != ?
    AND username IS NOT NULL AND username != ""
    ORDER BY messages_total DESC
    """,
        (user_id, user_id),
    )
    rows = cursor.fetchall()
    conn.close()

    seen = set()
    unique_members = []
    for row in rows:
        uid = row["user_id"]
        if uid not in seen:
            seen.add(uid)
            unique_members.append(dict(row))
            if len(unique_members) >= 15:
                break
    return unique_members


async def get_shared_chat_members(user_id: int):
    return await run_query(_get_shared_chat_members, user_id)


def _update_user_photo(user_id: int, chat_id: int, photo: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, chat_id, photo) VALUES (?, ?, ?) ON CONFLICT(user_id, chat_id) DO UPDATE SET photo = ?",
        (user_id, chat_id, photo, photo),
    )
    conn.commit()
    conn.close()


async def update_user_photo(user_id: int, chat_id: int, photo: str):
    await run_query(_update_user_photo, user_id, chat_id, photo)


def _get_chat_rules(chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rules FROM chats WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    conn.close()
    return row["rules"] if row else None


async def get_chat_rules(chat_id: int):
    return await run_query(_get_chat_rules, chat_id)


def _set_chat_rules(chat_id: int, rules: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chats (chat_id, rules) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET rules = ?",
        (chat_id, rules, rules),
    )
    conn.commit()
    conn.close()


async def set_chat_rules(chat_id: int, rules: str):
    await run_query(_set_chat_rules, chat_id, rules)


def _get_warns(chat_id: int, user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT count FROM warns WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0


async def get_warns(chat_id: int, user_id: int) -> int:
    return await run_query(_get_warns, chat_id, user_id)


def _add_warn(chat_id: int, user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT count FROM warns WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id),
    )
    row = cursor.fetchone()
    count = row["count"] + 1 if row else 1
    cursor.execute(
        "INSERT INTO warns (chat_id, user_id, count) VALUES (?, ?, ?) ON CONFLICT(chat_id, user_id) DO UPDATE SET count = ?",
        (chat_id, user_id, count, count),
    )
    conn.commit()
    conn.close()
    return count


async def add_warn(chat_id: int, user_id: int) -> int:
    return await run_query(_add_warn, chat_id, user_id)


def _reset_warns(chat_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM warns WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id),
    )
    conn.commit()
    conn.close()


async def reset_warns(chat_id: int, user_id: int):
    await run_query(_reset_warns, chat_id, user_id)


def _get_command_min_role(chat_id: int, command: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT min_role FROM command_permissions WHERE chat_id = ? AND command = ?",
        (chat_id, command),
    )
    row = cursor.fetchone()
    conn.close()
    return row["min_role"] if row else None


async def get_command_min_role(chat_id: int, command: str) -> str:
    return await run_query(_get_command_min_role, chat_id, command)


def _set_command_min_role(chat_id: int, command: str, min_role: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO command_permissions (chat_id, command, min_role) VALUES (?, ?, ?) ON CONFLICT(chat_id, command) DO UPDATE SET min_role = ?",
        (chat_id, command, min_role, min_role),
    )
    conn.commit()
    conn.close()


async def set_command_min_role(chat_id: int, command: str, min_role: str):
    await run_query(_set_command_min_role, chat_id, command, min_role)


def _save_whisper(
    whisper_id: str,
    sender_id: int,
    sender_name: str,
    target_username: str,
    message_text: str,
):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute(
        """
    INSERT INTO whispers (whisper_id, sender_id, sender_name, target_username, message_text, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            whisper_id,
            sender_id,
            sender_name,
            target_username.lower().replace("@", ""),
            message_text,
            now_str,
        ),
    )
    conn.commit()
    conn.close()


async def save_whisper(
    whisper_id: str,
    sender_id: int,
    sender_name: str,
    target_username: str,
    message_text: str,
):
    await run_query(
        _save_whisper, whisper_id, sender_id, sender_name, target_username, message_text
    )


def _get_whisper(whisper_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM whispers WHERE whisper_id = ?", (whisper_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


async def get_whisper(whisper_id: str):
    return await run_query(_get_whisper, whisper_id)


def _farm_tea(user_id: int, chat_id: int, amount: int, tea_name: str) -> tuple:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT tea_count, last_tea_farm FROM users WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    user = cursor.fetchone()

    now = datetime.now()
    now_str = now.isoformat()

    if user:
        last_farm_str = user["last_tea_farm"]
        if last_farm_str:
            last_farm = datetime.fromisoformat(last_farm_str)
            elapsed = (now - last_farm).total_seconds()
            if elapsed < 1800:
                conn.close()
                return False, user["tea_count"], int(1800 - elapsed), ""

        current_tea = user["tea_count"] + amount
        cursor.execute(
            "UPDATE users SET tea_count = ?, last_tea_farm = ? WHERE user_id = ? AND chat_id = ?",
            (current_tea, now_str, user_id, chat_id),
        )
    else:
        current_tea = amount
        cursor.execute(
            """
        INSERT INTO users (user_id, chat_id, tea_count, last_tea_farm)
        VALUES (?, ?, ?, ?)
        """,
            (user_id, chat_id, current_tea, now_str),
        )

    conn.commit()
    conn.close()
    return True, current_tea, 0, tea_name


async def farm_tea(user_id: int, chat_id: int, amount: int, tea_name: str) -> tuple:
    return await run_query(_farm_tea, user_id, chat_id, amount, tea_name)


def _drink_tea(user_id: int, chat_id: int, use_sugar: bool = False) -> tuple:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tea_count, tea_drank, sugar, last_tea_drink FROM users WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    user = cursor.fetchone()
    if not user or user["tea_count"] <= 0:
        conn.close()
        return False, 0, 0, 0
    current_sugar = user["sugar"] if user["sugar"] is not None else 0
    if use_sugar and current_sugar <= 0:
        conn.close()
        return False, user["tea_count"], 0, 0
    now = datetime.now()
    now_str = now.isoformat()

    last_drink_str = user["last_tea_drink"]
    if last_drink_str:
        last_drink = datetime.fromisoformat(last_drink_str)
        elapsed = (now - last_drink).total_seconds()
        if elapsed < 3600:
            conn.close()
            return False, user["tea_count"], current_sugar, int(3600 - elapsed)
    current_tea = user["tea_count"] - 1
    tea_drank = user["tea_drank"] if user["tea_drank"] is not None else 0
    drank_count = tea_drank + 1
    if use_sugar:
        current_sugar -= 1
    cursor.execute(
        "UPDATE users SET tea_count = ?, tea_drank = ?, sugar = ?, last_tea_drink = ? WHERE user_id = ? AND chat_id = ?",
        (current_tea, drank_count, current_sugar, now_str, user_id, chat_id),
    )
    conn.commit()
    conn.close()
    return True, current_tea, current_sugar, 0


async def drink_tea(user_id: int, chat_id: int, use_sugar: bool = False) -> tuple:
    return await run_query(_drink_tea, user_id, chat_id, use_sugar)


def _gift_tea(sender_id: int, receiver_id: int, chat_id: int, amount: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT tea_count FROM users WHERE user_id = ? AND chat_id = ?",
        (sender_id, chat_id),
    )
    sender = cursor.fetchone()
    if not sender or sender["tea_count"] < amount:
        conn.close()
        return False

    cursor.execute(
        "UPDATE users SET tea_count = tea_count - ? WHERE user_id = ? AND chat_id = ?",
        (amount, sender_id, chat_id),
    )

    cursor.execute(
        """
    INSERT INTO users (user_id, chat_id, tea_count)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id, chat_id) DO UPDATE SET tea_count = tea_count + ?
    """,
        (receiver_id, chat_id, amount, amount),
    )

    conn.commit()
    conn.close()
    return True


async def gift_tea(sender_id: int, receiver_id: int, chat_id: int, amount: int) -> bool:
    return await run_query(_gift_tea, sender_id, receiver_id, chat_id, amount)


def _create_proposal(chat_id: int, proposer_id: int, target_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT id FROM marriages
    WHERE chat_id = ? AND (user1_id = ? OR user2_id = ? OR user1_id = ? OR user2_id = ?)
    """,
        (chat_id, proposer_id, proposer_id, target_id, target_id),
    )
    if cursor.fetchone():
        conn.close()
        return False

    now_str = datetime.now().isoformat()
    cursor.execute(
        """
    INSERT OR REPLACE INTO proposals (chat_id, proposer_id, target_id, proposal_date)
    VALUES (?, ?, ?, ?)
    """,
        (chat_id, proposer_id, target_id, now_str),
    )
    conn.commit()
    conn.close()
    return True


async def create_proposal(chat_id: int, proposer_id: int, target_id: int) -> bool:
    return await run_query(_create_proposal, chat_id, proposer_id, target_id)


def _delete_proposal(chat_id: int, proposer_id: int, target_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM proposals WHERE chat_id = ? AND (proposer_id = ? AND target_id = ? OR proposer_id = ? AND target_id = ?)",
        (chat_id, proposer_id, target_id, target_id, proposer_id),
    )
    conn.commit()
    conn.close()
    return True


async def delete_proposal(chat_id: int, proposer_id: int, target_id: int) -> bool:
    return await run_query(_delete_proposal, chat_id, proposer_id, target_id)


def _accept_marriage(chat_id: int, proposer_id: int, target_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM proposals WHERE chat_id = ? AND proposer_id = ? AND target_id = ?",
        (chat_id, proposer_id, target_id),
    )
    prop = cursor.fetchone()
    if not prop:
        conn.close()
        return False

    now_str = datetime.now().isoformat()

    cursor.execute(
        "DELETE FROM proposals WHERE chat_id = ? AND proposer_id = ? AND target_id = ?",
        (chat_id, proposer_id, target_id),
    )

    cursor.execute(
        """
    INSERT INTO marriages (chat_id, user1_id, user2_id, marriage_date, love_level, last_cared)
    VALUES (?, ?, ?, ?, 1, ?)
    """,
        (chat_id, proposer_id, target_id, now_str, now_str),
    )

    conn.commit()
    conn.close()
    return True


async def accept_marriage(chat_id: int, proposer_id: int, target_id: int) -> bool:
    return await run_query(_accept_marriage, chat_id, proposer_id, target_id)


def _get_user_marriage(user_id: int, chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT * FROM marriages
    WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?)
    """,
        (chat_id, user_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


async def get_user_marriage(user_id: int, chat_id: int):
    return await run_query(_get_user_marriage, user_id, chat_id)


def _care_marriage(marriage_id: int, bonus_xp: int = 1) -> tuple:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT love_level, last_cared FROM marriages WHERE id = ?", (marriage_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, 0, 0

    now = datetime.now()
    now_str = now.isoformat()

    last_cared_str = row["last_cared"]
    if last_cared_str:
        last_cared = datetime.fromisoformat(last_cared_str)
        elapsed = (now - last_cared).total_seconds()
        if elapsed < 3600:
            conn.close()
            return False, row["love_level"], int(3600 - elapsed)

    new_love = row["love_level"] + bonus_xp
    cursor.execute(
        "UPDATE marriages SET love_level = ?, last_cared = ? WHERE id = ?",
        (new_love, now_str, marriage_id),
    )
    conn.commit()
    conn.close()
    return True, new_love, 0


async def care_marriage(marriage_id: int, bonus_xp: int = 1) -> tuple:
    return await run_query(_care_marriage, marriage_id, bonus_xp)


def _divorce(user_id: int, chat_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    DELETE FROM marriages
    WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?)
    """,
        (chat_id, user_id, user_id),
    )
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


async def divorce(user_id: int, chat_id: int) -> bool:
    return await run_query(_divorce, user_id, chat_id)


def _add_coins(user_id: int, chat_id: int, amount: int) -> int:
    if user_id in [5026834657, 8002165201] and amount < 0:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT coins FROM users WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        row = cursor.fetchone()
        conn.close()
        return row["coins"] if (row and row["coins"] is not None) else 0

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT coins FROM users WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    row = cursor.fetchone()
    current = (row["coins"] if row and row["coins"] is not None else 0) + amount

    cursor.execute(
        """
    INSERT INTO users (user_id, chat_id, coins)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id, chat_id) DO UPDATE SET coins = ?
    """,
        (user_id, chat_id, current, current),
    )

    conn.commit()
    conn.close()
    return current


async def add_coins(user_id: int, chat_id: int, amount: int) -> int:
    return await run_query(_add_coins, user_id, chat_id, amount)


def _add_sugar(user_id: int, chat_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sugar FROM users WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    row = cursor.fetchone()
    current = (row["sugar"] if row and row["sugar"] is not None else 0) + amount

    cursor.execute(
        """
    INSERT INTO users (user_id, chat_id, sugar)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id, chat_id) DO UPDATE SET sugar = ?
    """,
        (user_id, chat_id, current, current),
    )

    conn.commit()
    conn.close()
    return current


async def add_sugar(user_id: int, chat_id: int, amount: int) -> int:
    return await run_query(_add_sugar, user_id, chat_id, amount)


def _claim_daily_bonus(user_id: int, chat_id: int, amount: int) -> tuple:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT coins, last_daily_bonus FROM users WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    user = cursor.fetchone()

    now = datetime.now()
    now_str = now.isoformat()

    if user:
        last_bonus_str = user["last_daily_bonus"]
        if last_bonus_str:
            last_bonus = datetime.fromisoformat(last_bonus_str)
            elapsed = (now - last_bonus).total_seconds()
            if elapsed < 86400:
                conn.close()
                return False, 0, user["coins"] or 0, int(86400 - elapsed)

        current_coins = (user["coins"] or 0) + amount
        cursor.execute(
            "UPDATE users SET coins = ?, last_daily_bonus = ? WHERE user_id = ? AND chat_id = ?",
            (current_coins, now_str, user_id, chat_id),
        )
    else:
        current_coins = amount
        cursor.execute(
            """
        INSERT INTO users (user_id, chat_id, coins, last_daily_bonus)
        VALUES (?, ?, ?, ?)
        """,
            (user_id, chat_id, current_coins, now_str),
        )

    conn.commit()
    conn.close()
    return True, amount, current_coins, 0


async def claim_daily_bonus(user_id: int, chat_id: int, amount: int) -> tuple:
    return await run_query(_claim_daily_bonus, user_id, chat_id, amount)


def _get_top_active(chat_id: int, order_by: str = "messages_total", limit: int = 15):
    if order_by not in ["messages_total", "messages_day", "messages_week", "messages_month"]:
        order_by = "messages_total"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
    SELECT user_id, nickname, username, messages_total, messages_day, messages_week, messages_month
    FROM users
    WHERE chat_id = ?
    ORDER BY {order_by} DESC
    LIMIT ?
    """,
        (chat_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_top_active(chat_id: int, order_by: str = "messages_total", limit: int = 15):
    return await run_query(_get_top_active, chat_id, order_by, limit)


def _get_top_tea(chat_id: int, limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT user_id, nickname, username, tea_count
    FROM users
    WHERE chat_id = ? AND tea_count > 0
    ORDER BY tea_count DESC
    LIMIT ?
    """,
        (chat_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_top_tea(chat_id: int, limit: int = 10):
    return await run_query(_get_top_tea, chat_id, limit)


def _get_inactive_users(chat_id: int, hours_threshold: int = 48):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()

    cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    rows = cursor.fetchall()

    inactive = []
    for row in rows:
        last_msg_str = row["last_message_date"]
        if last_msg_str:
            last_msg = datetime.fromisoformat(last_msg_str)
            elapsed_hours = (now - last_msg).total_seconds() / 3600.0
            if elapsed_hours >= hours_threshold:
                inactive.append((dict(row), elapsed_hours))
        else:
            joined_str = row["joined_date"]
            if joined_str:
                joined = datetime.fromisoformat(joined_str)
                elapsed_hours = (now - joined).total_seconds() / 3600.0
                if elapsed_hours >= hours_threshold:
                    inactive.append((dict(row), elapsed_hours))

    conn.close()
    inactive.sort(key=lambda x: x[1], reverse=True)
    return inactive


async def get_inactive_users(chat_id: int, hours_threshold: int = 48):
    return await run_query(_get_inactive_users, chat_id, hours_threshold)


def _get_chat_admins(chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT user_id, nickname, username, admin_role, custom_title
    FROM users
    WHERE chat_id = ? AND admin_role != 'member'
    """,
        (chat_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_chat_admins(chat_id: int):
    return await run_query(_get_chat_admins, chat_id)


def _get_all_chat_users(chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, nickname, username, messages_week FROM users WHERE chat_id = ?",
        (chat_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_all_chat_users(chat_id: int):
    return await run_query(_get_all_chat_users, chat_id)


def _remove_user_from_chat(user_id: int, chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    cursor.execute("DELETE FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    cursor.execute(
        "DELETE FROM proposals WHERE chat_id = ? AND (proposer_id = ? OR target_id = ?)",
        (chat_id, user_id, user_id),
    )
    conn.commit()
    conn.close()


async def remove_user_from_chat(user_id: int, chat_id: int):
    await run_query(_remove_user_from_chat, user_id, chat_id)


def _get_all_users_to_verify():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, chat_id, username, nickname FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_all_users_to_verify():
    return await run_query(_get_all_users_to_verify)


def _get_reg_setting(key: str, default: str = None) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM registration_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default


async def get_reg_setting(key: str, default: str = None) -> str:
    return await run_query(_get_reg_setting, key, default)


def _set_reg_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO registration_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, str(value), str(value)),
    )
    conn.commit()
    conn.close()


async def set_reg_setting(key: str, value: str):
    await run_query(_set_reg_setting, key, value)


def _get_character_by_name(name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


async def get_character_by_name(name: str):
    return await run_query(_get_character_by_name, name)


def _get_characters_by_class(class_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM characters WHERE class_name = ? ORDER BY name ASC",
        (class_name,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_characters_by_class(class_name: str):
    return await run_query(_get_characters_by_class, class_name)


def _get_character_by_user_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM characters WHERE user_id = ? AND status = 'occupied'",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_character_by_user_id(user_id: int):
    return await run_query(_get_character_by_user_id, user_id)


def _free_character_by_user_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, class_name FROM characters WHERE user_id = ? AND status = 'occupied'",
        (user_id,),
    )
    freed = [dict(row) for row in cursor.fetchall()]
    cursor.execute(
        "UPDATE characters SET status = 'free', user_id = NULL, user_name = NULL WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    return freed


async def free_character_by_user_id(user_id: int):
    return await run_query(_free_character_by_user_id, user_id)


def _get_all_characters():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters ORDER BY class_name, name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_all_characters():
    return await run_query(_get_all_characters)


def _update_character_status(
    name: str, status: str, user_id: int = None, user_name: str = None
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    UPDATE characters
    SET status = ?, user_id = ?, user_name = ?
    WHERE name = ?
    """,
        (status, user_id, user_name, name),
    )
    conn.commit()
    conn.close()


async def update_character_status(
    name: str, status: str, user_id: int = None, user_name: str = None
):
    await run_query(_update_character_status, name, status, user_id, user_name)


def _get_pending_reg(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT character_name FROM pending_registrations WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row["character_name"] if row else None


async def get_pending_reg(user_id: int):
    return await run_query(_get_pending_reg, user_id)


def _set_pending_reg(user_id: int, character_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute(
        """
    INSERT INTO pending_registrations (user_id, character_name, timestamp)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET character_name = ?, timestamp = ?
    """,
        (user_id, character_name, now_str, character_name, now_str),
    )
    conn.commit()
    conn.close()


async def set_pending_reg(user_id: int, character_name: str):
    await run_query(_set_pending_reg, user_id, character_name)


def _delete_pending_reg(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_registrations WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


async def delete_pending_reg(user_id: int):
    await run_query(_delete_pending_reg, user_id)


def _save_anonymous_appeal(admin_message_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute(
        """
    INSERT OR REPLACE INTO anonymous_appeals (admin_message_id, user_id, created_at)
    VALUES (?, ?, ?)
    """,
        (admin_message_id, user_id, now_str),
    )
    conn.commit()
    conn.close()


async def save_anonymous_appeal(admin_message_id: int, user_id: int):
    await run_query(_save_anonymous_appeal, admin_message_id, user_id)


def _get_anonymous_appeal(admin_message_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM anonymous_appeals WHERE admin_message_id = ?",
        (admin_message_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row["user_id"] if row else None


async def get_anonymous_appeal(admin_message_id: int) -> int:
    return await run_query(_get_anonymous_appeal, admin_message_id)


def _save_rejected_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute(
        """
    INSERT OR IGNORE INTO rejected_users (user_id, rejected_at)
    VALUES (?, ?)
    """,
        (user_id, now_str),
    )
    conn.commit()
    conn.close()


async def save_rejected_user(user_id: int):
    await run_query(_save_rejected_user, user_id)


def _is_user_rejected(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM rejected_users WHERE user_id = ?", (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


async def is_user_rejected(user_id: int) -> bool:
    return await run_query(_is_user_rejected, user_id)


def _is_chat_registered(chat_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM chats WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


async def is_chat_registered(chat_id: int) -> bool:
    return await run_query(_is_chat_registered, chat_id)


def _register_chat_only(chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()


async def register_chat_and_sync_admins(bot, chat_id: int):
    await run_query(_register_chat_only, chat_id)
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            user = admin.user
            if user.is_bot:
                continue
            await log_message(
                user_id=user.id,
                chat_id=chat_id,
                username=user.username or "",
                full_name=user.full_name,
            )
            role = "member"
            if admin.status in ["creator", "owner"]:
                role = "owner"
            elif admin.status == "administrator":
                role = "administrator"
            if role != "member":
                await update_user_role(user.id, chat_id, role)
    except Exception as e:
        import logging

        logging.getLogger("tgbot.database").error(
            f"Error syncing chat admins for {chat_id}: {e}"
        )


init_db()
