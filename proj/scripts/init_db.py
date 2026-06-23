import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "altmart.db")

def init_all():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Таблица приложений
    cursor.execute('CREATE TABLE IF NOT EXISTS apps (id INTEGER PRIMARY KEY, is_game INTEGER, category_code TEXT, data JSON)')
    # Таблица отзывов
    cursor.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, app_id INTEGER, user_id INTEGER, rating INTEGER, comment TEXT, data JSON)')
    # Таблица юзеров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            avatar TEXT DEFAULT 'avatar1.png',
            is_premium INTEGER DEFAULT 0,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Добавляем тебя
    cursor.execute("INSERT OR IGNORE INTO users (id, username, password, is_premium) VALUES (503, 'vitalokek2', '12345', 1)")
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована.")

if __name__ == "__main__":
    init_all()
