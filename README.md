# AltMart Server

Лёгкий self-hosted сервер для каталога Android-приложений (форк протокола oldmarket).
FastAPI + aiosqlite, без SQLAlchemy/Flask — минимум зависимостей.

## Установка

```bash
pip install -r requirements.txt
# опционально, для tui.py и live_scrapper.py:
pip install -r requirements-tools.txt
```

## Первый запуск

```bash
python3 scripts/init_db.py
```
Скрипт спросит логин/пароль и создаст структуру БД + premium-аккаунт.
**Пароль не хранится в коде** — вводится интерактивно и сразу хешируется (bcrypt).

Положите скачанные APK/иконки/скриншоты в `downloaded/apks`, `downloaded/html/...`
(структура папок видна в `main.py`, в `static_dirs`) — этот каталог в `.gitignore`,
он не должен попадать в git.

## Запуск сервера

```bash
python3 main.py
# или
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Управление (CLI и TUI)

```bash
python3 cli.py db stats
python3 cli.py user create --name vitalokek2   # спросит пароль интерактивно
python3 tui.py                                  # графическая панель на rich
```