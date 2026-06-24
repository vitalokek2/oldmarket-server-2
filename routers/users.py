import json
import os

import bcrypt
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from database import fetch_all, fetch_one, execute_query
from security import get_real_ip, check_registration_rate_limit, increment_registration_ip, check_login_bruteforce, record_login_attempt, is_ip_blocked, ban_ip

router = APIRouter(prefix="/api")

@router.get("/me")
async def get_me(request: Request):
    """Текущий авторизованный пользователь."""
    session_id = request.cookies.get("session_user_id")
    if not session_id:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    try:
        user_id = int(session_id)
    except ValueError:
        return JSONResponse(status_code=401, content={"error": "Invalid session"})

    user = await fetch_one("SELECT id, username, avatar, description, is_premium FROM users WHERE id = ?", (user_id,))
    if not user:
        return JSONResponse(status_code=401, content={"error": "User not found"})
    return {
        "id": user["id"],
        "username": user["username"],
        "avatar": user["avatar"],
        "description": user["description"],
        "is_premium": user["is_premium"],
    }

@router.get("/user/{user_id}/profile")
async def get_user_profile(user_id: int):
    user = await fetch_one("SELECT id, username, avatar, description, is_premium, reg_date FROM users WHERE id = ?", (user_id,))
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    return {
        "id": user["id"],
        "username": user["username"],
        "avatar": user["avatar"],
        "description": user["description"],
        "is_premium": user["is_premium"],
        "reg_date": user["reg_date"],
    }

@router.put("/user/{user_id}/profile")
async def update_user_profile(user_id: int, request: Request):
    """Обновление профиля (avatar + description). Требует авторизации."""
    session_id = request.cookies.get("session_user_id")
    if not session_id or int(session_id) != user_id:
        return JSONResponse(status_code=403, content={"success": False, "message": "Доступ запрещён"})

    try:
        data = await request.json()
        avatar = data.get("avatar")
        description = data.get("description", "")

        if avatar:
            await execute_query(
                "UPDATE users SET avatar = ?, description = ? WHERE id = ?",
                (avatar, description, user_id)
            )
        else:
            await execute_query(
                "UPDATE users SET description = ? WHERE id = ?",
                (description, user_id)
            )
        return {"success": True, "message": "Профиль обновлён"}
    except Exception as e:
        print(f"Ошибка обновления профиля: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})

@router.post("/register")
async def register(request: Request):
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        ip = get_real_ip(request)

        if not username or not password:
            return JSONResponse(status_code=400, content={"success": False, "message": "Логин и пароль обязательны"})
        if len(password.encode("utf-8")) > 72:
            return JSONResponse(status_code=400, content={"success": False, "message": "Пароль слишком длинный"})

        if await is_ip_blocked(ip):
            return JSONResponse(status_code=403, content={"success": False, "message": "Ваш IP заблокирован"})

        if not await check_registration_rate_limit(ip):
            await ban_ip(ip, "Превышен лимит регистраций", hours=24)
            return JSONResponse(status_code=429, content={"success": False, "message": "Слишком много регистраций с вашего IP"})

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        try:
            await execute_query("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            await increment_registration_ip(ip)
        except Exception:
            return JSONResponse(status_code=400, content={"success": False, "message": "Имя пользователя уже занято"})

        return {"success": True, "message": "Регистрация успешна"}
    except Exception as e:
        print(f"Ошибка регистрации: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})

@router.post("/login")
async def login(request: Request):
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        ip = get_real_ip(request)

        if not username or not password:
            return JSONResponse(status_code=400, content={"success": False, "message": "Логин и пароль обязательны"})

        if await is_ip_blocked(ip):
            return JSONResponse(status_code=403, content={"success": False, "message": "Ваш IP заблокирован"})

        if await check_login_bruteforce(ip):
            return JSONResponse(status_code=429, content={"success": False, "message": "Слишком много неудачных попыток. Попробуйте позже."})

        user = await fetch_one("SELECT id, password FROM users WHERE username = ?", (username,))
        if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            await record_login_attempt(ip, username, False)
            return JSONResponse(status_code=401, content={"success": False, "message": "Неверный логин или пароль"})

        await record_login_attempt(ip, username, True)
        response = JSONResponse(content={"success": True, "message": "Вход выполнен", "user_id": user["id"]})
        response.set_cookie(key="session_user_id", value=str(user["id"]), httponly=True, max_age=2592000)
        return response

    except Exception as e:
        print(f"Ошибка входа: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})

@router.post("/logout")
async def logout():
    response = JSONResponse(content={"success": True, "message": "Выход выполнен"})
    response.delete_cookie("session_user_id")
    return response
