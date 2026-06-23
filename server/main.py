#!/usr/bin/env python3
import os
import sqlite3
import json
from typing import List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Cookie, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "altmart.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Создаем папки под загрузки, если их нет
os.makedirs(os.path.join(STATIC_DIR, "apks"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "icons"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "screenshots"), exist_ok=True)

app = FastAPI(title="AltMart API")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица приложений
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        package TEXT UNIQUE,
        is_game INTEGER DEFAULT 0,
        category_code TEXT DEFAULT 'tools',
        apk_file TEXT,
        icon TEXT,
        author TEXT DEFAULT 'Anonymous',
        description TEXT DEFAULT '',
        min_android TEXT DEFAULT '5.0+',
        downloads INTEGER DEFAULT 0,
        rating REAL DEFAULT 5.0,
        screenshots TEXT DEFAULT '[]'
    )""")
    
    # Таблица пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")
    
    # Таблица комментариев
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_id INTEGER,
        username TEXT,
        text TEXT,
        rating INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

init_db()

# Модели для авторизации
class AuthModel(BaseModel):
    username: str
    password: str

class CommentModel(BaseModel):
    text: str
    rating: int

# Помощник получения текущего юзера по кукам
def get_current_user(session_user: str = Cookie(None)):
    if not session_user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return session_user

# --- ЭНДПОИНТЫ API ---

@app.get("/api/apps")
def get_apps():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    apps = conn.execute("SELECT * FROM apps ORDER BY downloads DESC").fetchall()
    conn.close()
    return [dict(row) for row in apps]

@app.get("/api/apps/{app_id}")
def get_app(app_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    app_data = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    if not app_data:
        raise HTTPException(status_code=404, detail="Приложение не найдено")
    return dict(app_data)

# Эндпоинт скриншотов строго по скриншоту юзера!
@app.get("/api/app/{app_id}/screenshots")
def get_app_screenshots(app_id: int):
    conn = sqlite3.connect(DB_PATH)
    res = conn.execute("SELECT screenshots FROM apps WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    if not res:
        return []
    return json.loads(res[0])

# Загрузка нового приложения пользователем
@app.post("/api/apps/upload")
async def upload_app(
    name: str = Form(...),
    package: str = Form(...),
    is_game: int = Form(0),
    category_code: str = Form("tools"),
    author: str = Form("Anonymous"),
    description: str = Form(""),
    min_android: str = Form("4.1+"),
    apk: UploadFile = File(...),
    icon: UploadFile = File(...),
    screenshots: List[UploadFile] = File([])
):
    # Сохраняем APK
    apk_filename = f"{package}.apk"
    with open(os.path.join(STATIC_DIR, "apks", apk_filename), "wb") as f:
        f.write(await apk.read())
        
    # Сохраняем Иконку
    icon_filename = f"{package}_icon.png"
    with open(os.path.join(STATIC_DIR, "icons", icon_filename), "wb") as f:
        f.write(await icon.read())

    # Сохраняем Скриншоты
    scr_names = []
    for idx, scr in enumerate(screenshots):
        scr_name = f"{package}_scr_{idx}.jpg"
        with open(os.path.join(STATIC_DIR, "screenshots", scr_name), "wb") as f:
            f.write(await scr.read())
        scr_names.append(scr_name)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO apps (name, package, is_game, category_code, apk_file, icon, author, description, min_android, screenshots)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, package, is_game, category_code, apk_filename, icon_filename, author, description, min_android, json.dumps(scr_names)))
    conn.commit()
    conn.close()
    return {"status": "success"}

# Скачивание (увеличение счетчика)
@app.get("/api/apps/{app_id}/download")
def download_counter(app_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE apps SET downloads = downloads + 1 WHERE id = ?", (app_id,))
    conn.commit()
    app_data = conn.execute("SELECT apk_file FROM apps WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    if app_data:
        return {"file": app_data[0]}
    raise HTTPException(status_code=404)

# --- СИСТЕМА КОММЕНТАРИЕВ ---
@app.get("/api/app/{app_id}/comments")
def get_comments(app_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    comments = conn.execute("SELECT * FROM comments WHERE app_id = ? ORDER BY created_at DESC", (app_id,)).fetchall()
    conn.close()
    return [dict(c) for c in comments]

@app.post("/api/app/{app_id}/comments")
def add_comment(app_id: int, data: CommentModel, user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO comments (app_id, username, text, rating) VALUES (?, ?, ?, ?)",
                 (app_id, user, data.text, data.rating))
    # Пересчет среднего рейтинга приложения
    avg_rating = conn.execute("SELECT AVG(rating) FROM comments WHERE app_id = ?", (app_id,)).fetchone()[0]
    if avg_rating:
        conn.execute("UPDATE apps SET rating = ? WHERE id = ?", (round(avg_rating, 1), app_id))
    conn.commit()
    conn.close()
    return {"status": "added"}

# --- СИСТЕМА АККАУНТОВ ---
@app.post("/api/auth/register")
def register(data: AuthModel):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (data.username, data.password))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Имя пользователя занято")
    finally:
        conn.close()
    return {"status": "registered"}

@app.post("/api/auth/login")
def login(data: AuthModel):
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (data.username, data.password)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")
    response = JSONResponse(content={"status": "logged_in", "username": data.username})
    response.set_cookie(key="session_user", value=data.username, max_age=86400 * 30)
    return response

@app.post("/api/auth/logout")
def logout():
    response = JSONResponse(content={"status": "logged_out"})
    response.delete_cookie("session_user")
    return response

@app.delete("/api/auth/delete_account")
def delete_account(user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM users WHERE username = ?", (user,))
    conn.commit()
    conn.close()
    response = JSONResponse(content={"status": "deleted"})
    response.delete_cookie("session_user")
    return response

# Отдача статики
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=FileResponse)
def read_root():
    return os.path.join(STATIC_DIR, "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
