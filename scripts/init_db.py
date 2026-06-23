import os
import sqlite3
import getpass

import bcrypt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "altmart.db")


def init_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS apps (id INTEGER PRIMARY KEY, is_game INTEGER, category_code TEXT, data JSON)")
    cursor.execute("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, app_id INTEGER, user_id INTEGER, rating INTEGER, comment TEXT, data JSON)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            avatar TEXT DEFAULT 'avatar1.png',
            description TEXT DEFAULT '',
            is_premium INTEGER DEFAULT 0,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Структура базы данных инициализирована.")


def create_admin_account():
    """Интерактивно создаёт первый (админский) аккаунт — без пароля в коде."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existing = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        print("ℹ️  Пользователи уже есть в базе, пропускаю создание админа.")
        conn.close()
        return

    username = input("Логин для твоего аккаунта: ").strip()
    password = getpass.getpass("Пароль (не будет показан): ").strip()
    if not username or not password:
        print("⚠️  Логин/пароль не заданы, аккаунт не создан.")
        conn.close()
        return
    if len(password.encode("utf-8")) > 72:
        print("⚠️  Пароль слишком длинный (макс. 72 байта), аккаунт не создан.")
        conn.close()
        return

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cursor.execute(
        "INSERT INTO users (username, password, is_premium) VALUES (?, ?, 1)",
        (username, hashed),
    )
    conn.commit()
    conn.close()
    print(f"✅ Аккаунт '{username}' создан с premium-статусом.")


def init_all():
    init_schema()
    create_admin_account()


if __name__ == "__main__":
    init_all()
