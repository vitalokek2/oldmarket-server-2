#!/usr/bin/env python3
import argparse
import getpass
import os
import sys
import json
import sqlite3
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

import bcrypt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "altmart.db")
SERVICE_NAME = "altmart.service"
SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}"

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
C = "\033[96m"
B = "\033[1m"
RESET = "\033[0m"

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def handle_service(args):
    if args.action == "install":
        if os.path.exists(SERVICE_PATH):
            print(f"{Y}Служба уже установлена.{RESET}")
            return
        current_user = os.getlogin()
        python_path = sys.executable
        main_script = os.path.join(BASE_DIR, "main.py")
        service_content = f"""[Unit]
Description=AltMart FastAPI Server Daemon
After=network.target

[Service]
User={current_user}
WorkingDirectory={BASE_DIR}
ExecStart={python_path} {main_script}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
        print(f"{C}Создаю системный юнит {SERVICE_PATH}...{RESET}")
        try:
            p = subprocess.Popen(['sudo', 'tee', SERVICE_PATH], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            p.communicate(input=service_content)
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', SERVICE_NAME], check=True)
            subprocess.run(['sudo', 'systemctl', 'start', SERVICE_NAME], check=True)
            print(f"{G}✅ Демон AltMart успешно развернут и запущен в systemd!{RESET}")
        except Exception as e:
            print(f"{R}❌ Ошибка прав доступа или выполнения: {e}{RESET}")
    elif args.action in ["start", "stop", "restart", "status"]:
        cmd = ['sudo', 'systemctl', args.action, SERVICE_NAME] if args.action != "status" else ['systemctl', 'status', SERVICE_NAME]
        subprocess.run(cmd)

def handle_db(args):
    if args.action == "init":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS apps (id INTEGER PRIMARY KEY, is_game INTEGER, category_code TEXT, data JSON)')
        cursor.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, app_id INTEGER, user_id INTEGER, rating INTEGER, comment TEXT, data JSON)')
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    avatar TEXT DEFAULT 'avatar1.png',
    description TEXT DEFAULT '',
    is_premium INTEGER DEFAULT 0,
    reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    author TEXT NOT NULL,
    category_code TEXT NOT NULL,
    data JSON NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
        conn.commit()
        conn.close()
        print(f"{G}✅ Структура базы данных инициализирована.{RESET}")
        print(f"{Y}ℹ️ Аккаунт не создан автоматически — используй `altmart user create` чтобы завести себе аккаунт с паролем.{RESET}")
    elif args.action == "stats":
        if not os.path.exists(DB_PATH):
            print(f"{R}База данных не найдена. Выполни сначала db init{RESET}")
            return
        conn = get_db_conn()
        apps_cnt = conn.execute("SELECT COUNT(*) FROM apps WHERE is_game=0").fetchone()[0]
        games_cnt = conn.execute("SELECT COUNT(*) FROM apps WHERE is_game=1").fetchone()[0]
        users_cnt = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        revs_cnt = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        pending_cnt = conn.execute("SELECT COUNT(*) FROM submissions WHERE status='pending'").fetchone()[0]
        conn.close()
        print(f"{B}{C}=== СТАТИСТИКА ALTMART ==={RESET}")
        print(f"Программы на витрине: {G}{apps_cnt}{RESET}")
        print(f"Игры на витрине: {G}{games_cnt}{RESET}")
        print(f"Пользователи: {G}{users_cnt}{RESET}")
        print(f"Всего отзывов: {G}{revs_cnt}{RESET}")
        print(f"Заявок на модерацию: {Y}{pending_cnt}{RESET}")
    elif args.action == "backup":
        if not os.path.exists(DB_PATH): return
        out_path = args.out if args.out else os.path.join(BASE_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        subprocess.run(['cp', DB_PATH, out_path])
        print(f"{G}✅ Бекап успешно сохранен в: {out_path}{RESET}")
    elif args.action == "wipe":
        if not args.force:
            conf = input(f"{R}{B}⚠️ Ты действительно хочешь УНИЧТОЖИТЬ всю базу данных? (y/N): {RESET}")
            if conf.lower() != 'y': return
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print(f"{Y}База снесена. Пересоздаю чистую структуру...{RESET}")
            class Dummy: action = "init"
            handle_db(Dummy())

def handle_app(args):
    conn = get_db_conn()
    if args.action == "add":
        app_data = {
            "id": args.id, "name": args.name, "package": args.pkg,
            "downloads": args.downloads, "icon": "default_icon.png",
            "apk_file": args.apk, "screenshots": [],
            "versions": [{"version_name": "1.0", "version_code": 1, "apk_file": args.apk}]
        }
        conn.execute("INSERT OR REPLACE INTO apps (id, is_game, category_code, data) VALUES (?, ?, ?, ?)",
            (args.id, args.is_game, args.cat, json.dumps(app_data, ensure_ascii=False)))
        conn.commit()
        print(f"{G}✅ Приложение '{args.name}' добавлено/обновлено в базе.{RESET}")
    elif args.action == "remove":
        conn.execute("DELETE FROM apps WHERE id = ?", (args.id,))
        conn.commit()
        print(f"{G}✅ Приложение с ID {args.id} удалено.{RESET}")
    elif args.action == "list":
        query = "SELECT id, is_game, category_code, data FROM apps"
        if args.games: query += " WHERE is_game = 1"
        elif args.apps: query += " WHERE is_game = 0"
        query += f" LIMIT {args.limit}"
        rows = conn.execute(query).fetchall()
        print(f"{B}{C}{'ID':<6} | {'Тип':<5} | {'Категория':<10} | {'Название':<25} | {'Пакет'}{RESET}")
        print("-" * 75)
        for r in rows:
            data = json.loads(r["data"])
            type_str = "Игра" if r["is_game"] == 1 else "Софт"
            print(f"{r['id']:<6} | {type_str:<5} | {r['category_code']:<10} | {data.get('name', 'N/A'):<25} | {data.get('package', 'N/A')}")
    conn.close()

def handle_user(args):
    conn = get_db_conn()
    if args.action == "create":
        password = args.text_pass
        if not password:
            password = getpass.getpass("Пароль для нового пользователя (не будет показан): ")
        if len(password.encode("utf-8")) > 72:
            print(f"{R}❌ Пароль слишком длинный (макс. 72 байта).{RESET}")
            return
        try:
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (args.name, hashed))
            conn.commit()
            print(f"{G}✅ Пользователь {args.name} успешно создан.{RESET}")
        except sqlite3.IntegrityError:
            print(f"{R}❌ Ошибка: Пользователь с таким именем уже существует.{RESET}")
    elif args.action == "premium":
        field = "id" if args.user_id.isdigit() else "username"
        conn.execute(f"UPDATE users SET is_premium = ? WHERE {field} = ?", (args.status, args.user_id))
        conn.commit()
        print(f"{G}✅ Статус Premium для юзера {args.user_id} изменен на {args.status}.{RESET}")
    elif args.action == "list":
        rows = conn.execute("SELECT id, username, is_premium, reg_date FROM users").fetchall()
        print(f"{B}{C}{'ID':<5} | {'Имя пользователя':<20} | {'Premium':<7} | {'Дата регистрации'}{RESET}")
        print("-" * 60)
        for r in rows:
            prem = f"{G}Да{RESET}" if r["is_premium"] == 1 else "Нет"
            print(f"{r['id']:<5} | {r['username']:<20} | {prem:<7} | {r['reg_date']}")
    conn.close()

def handle_submissions(args):
    conn = get_db_conn()
    if args.action == "list":
        status_filter = args.status if args.status else "pending"
        rows = conn.execute(
            "SELECT id, name, author, category_code, status, created_at FROM submissions WHERE status = ? ORDER BY id DESC",
            (status_filter,)
        ).fetchall()
        if not rows:
            print(f"{Y}Заявок со статусом '{status_filter}' нет.{RESET}")
            conn.close()
            return
        print(f"{B}{C}{'ID':<5} | {'Название':<28} | {'Автор':<15} | {'Категория':<15} | {'Статус':<10} | {'Дата'}{RESET}")
        print("-" * 100)
        for r in rows:
            status_color = G if r["status"] == "approved" else (R if r["status"] == "rejected" else Y)
            print(f"{r['id']:<5} | {r['name']:<28} | {r['author']:<15} | {r['category_code']:<15} | {status_color}{r['status']:<10}{RESET} | {r['created_at']}")
    elif args.action == "view":
        row = conn.execute("SELECT * FROM submissions WHERE id = ?", (args.id,)).fetchone()
        if not row:
            print(f"{R}❌ Заявка #{args.id} не найдена.{RESET}")
            conn.close()
            return
        data = json.loads(row["data"])
        print(f"{B}{C}=== ЗАЯВКА #{row['id']} ==={RESET}")
        print(f"Название: {row['name']}")
        print(f"Автор: {row['author']}")
        print(f"Package: {data.get('package', '—')}")
        print(f"Категория: {row['category_code']}")
        print(f"Статус: {row['status']}")
        print(f"Описание: {data.get('description', '—')}")
        print(f"Версия: {data.get('version', '—')} (code: {data.get('version_code', '—')})")
        print(f"Min Android API: {data.get('min_android', '—')}")
        print(f"APK файл: {data.get('apk_file', '—')}")
        print(f"Иконка: {data.get('icon', '—')}")
        print(f"Дата подачи: {row['created_at']}")
        if data.get('reject_reason'):
            print(f"{R}Причина отклонения: {data['reject_reason']}{RESET}")
    elif args.action == "approve":
        row = conn.execute("SELECT * FROM submissions WHERE id = ?", (args.id,)).fetchone()
        if not row:
            print(f"{R}❌ Заявка #{args.id} не найдена.{RESET}")
            conn.close()
            return
        if row["status"] != "pending":
            print(f"{R}❌ Заявка уже обработана (статус: {row['status']}).{RESET}")
            conn.close()
            return
        data = json.loads(row["data"])
        max_id = conn.execute("SELECT MAX(id) as max_id FROM apps").fetchone()["max_id"] or 0
        new_id = max_id + 1
        base = Path(BASE_DIR)
        upload_dir = base / "downloaded" / "submissions"
        apks_dir = base / "downloaded" / "apks"
        icons_dir = base / "downloaded" / "html" / "apps"
        apk_src = upload_dir / data["apk_file"]
        apk_dest = apks_dir / data["apk_file"]
        if apk_src.exists():
            shutil.move(str(apk_src), str(apk_dest))
        icon_name = data.get("icon", "")
        if icon_name:
            icon_src = upload_dir / icon_name
            icon_dest = icons_dir / icon_name
            if icon_src.exists():
                shutil.move(str(icon_src), str(icon_dest))
        game_cats = {"simulators", "puzzles", "arcade", "races", "action_games", "casual",
                     "strategies", "table_games", "shooter", "horror", "adventures", "rpg",
                     "survival", "sport", "card_games", "other_games"}
        is_game = 1 if row["category_code"] in game_cats else 0
        app_json = {
            "id": new_id,
            "name": data["name"],
            "author": data["author"],
            "package": data.get("package", ""),
            "description": data["description"],
            "version": data.get("version", "1.0"),
            "version_code": data.get("version_code", "1"),
            "apk_file": data["apk_file"],
            "icon": icon_name or "default_icon.png",
            "screenshots": data.get("screenshots", []),
            "category_code": row["category_code"],
            "category_label": data.get("category_label", row["category_code"]),
            "is_game": bool(is_game),
            "downloads": 0,
            "rating": 0.0,
            "review_count": 0,
        }
        if data.get("min_android"):
            app_json["api"] = data["min_android"]
        app_json["versions"] = [{
            "version_name": data.get("version", "1.0"),
            "version_code": data.get("version_code", "1"),
            "apk_file": data["apk_file"],
        }]
        conn.execute(
            "INSERT INTO apps (id, is_game, category_code, data) VALUES (?, ?, ?, ?)",
            (new_id, is_game, row["category_code"], json.dumps(app_json, ensure_ascii=False))
        )
        conn.execute("UPDATE submissions SET status = 'approved' WHERE id = ?", (args.id,))
        conn.commit()
        print(f"{G}✅ Заявка #{args.id} одобрена! Приложение добавлено с ID {new_id}.{RESET}")
    elif args.action == "reject":
        row = conn.execute("SELECT * FROM submissions WHERE id = ?", (args.id,)).fetchone()
        if not row:
            print(f"{R}❌ Заявка #{args.id} не найдена.{RESET}")
            conn.close()
            return
        data = json.loads(row["data"])
        data["reject_reason"] = args.reason or ""
        conn.execute(
            "UPDATE submissions SET status = 'rejected', data = ? WHERE id = ?",
            (json.dumps(data, ensure_ascii=False), args.id)
        )
        conn.commit()
        print(f"{Y}⚠️ Заявка #{args.id} отклонена.{RESET}")
    conn.close()

def handle_logs(args):
    cmd = ['journalctl', '-u', SERVICE_NAME, '-n', str(args.lines)]
    if args.follow: cmd.append('-f')
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nВыход из режима просмотра логов.")

def main():
    parser = argparse.ArgumentParser(description=f"{B}{C}AltMart CLI Manager v2.0{RESET}", usage="%(prog)s [команда] [опции]")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_service = subparsers.add_parser("service", help="Управление службой systemd")
    p_service.add_argument("action", choices=["install", "start", "stop", "restart", "status"], help="Действие со службой")
    p_service.set_defaults(func=handle_service)

    p_db = subparsers.add_parser("db", help="Управление базой данных SQLite")
    p_db.add_argument("action", choices=["init", "stats", "backup", "wipe"], help="Действие с БД")
    p_db.add_argument("--out", help="Путь для сохранения бекапа")
    p_db.add_argument("--force", action="store_true", help="Пропустить подтверждение при полном удалении базы")
    p_db.set_defaults(func=handle_db)

    p_app = subparsers.add_parser("app", help="Управление приложениями на витрине")
    p_app.add_argument("action", choices=["add", "remove", "list"], help="Действие с приложениями")
    p_app.add_argument("--id", type=int, help="ID приложения")
    p_app.add_argument("--name", help="Название приложения")
    p_app.add_argument("--pkg", help="Имя пакета (package_name)")
    p_app.add_argument("--cat", default="tools", help="Код категории")
    p_app.add_argument("--is-game", type=int, choices=[0, 1], default=0, help="1 — игра, 0 — приложение")
    p_app.add_argument("--apk", help="Имя APK файла")
    p_app.add_argument("--downloads", default="0", help="Отображаемые скачивания")
    p_app.add_argument("--games", action="store_true", help="Показать только игры (для списка)")
    p_app.add_argument("--apps", action="store_true", help="Показать только софт (для списка)")
    p_app.add_argument("--limit", type=int, default=20, help="Лимит вывода строк для списка")
    p_app.set_defaults(func=handle_app)

    p_user = subparsers.add_parser("user", help="Администрирование пользователей")
    p_user.add_argument("action", choices=["create", "premium", "list"], help="Действие с аккаунтами")
    p_user.add_argument("--name", help="Имя нового пользователя")
    p_user.add_argument("--text-pass", help="Пароль пользователя")
    p_user.add_argument("--user-id", help="ID или Имя пользователя для выдачи премиума")
    p_user.add_argument("--status", type=int, choices=[0, 1], default=1, help="1 — включить премиум, 0 — выключить")
    p_user.set_defaults(func=handle_user)

    p_sub = subparsers.add_parser("submissions", help="Модерация заявок на добавление приложений")
    p_sub.add_argument("action", choices=["list", "view", "approve", "reject"], help="Действие")
    p_sub.add_argument("--id", type=int, help="ID заявки (для view/approve/reject)")
    p_sub.add_argument("--status", choices=["pending", "approved", "rejected"], default="pending", help="Фильтр статуса (для list)")
    p_sub.add_argument("--reason", help="Причина отклонения (для reject)")
    p_sub.set_defaults(func=handle_submissions)

    p_logs = subparsers.add_parser("logs", help="Просмотр системных логов сервера")
    p_logs.add_argument("-f", "--follow", action="store_true", help="Стримить логи в реальном времени (как tail -f)")
    p_logs.add_argument("-n", "--lines", type=int, default=50, help="Количество выводимых строк с конца")
    p_logs.set_defaults(func=handle_logs)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
