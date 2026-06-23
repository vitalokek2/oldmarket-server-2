import bcrypt
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse

from database import fetch_one, execute_query
from security import (
    get_real_ip,
    is_ip_blocked,
    ban_ip,
    check_registration_rate_limit,
    increment_registration_ip,
    record_login_attempt,
    check_login_bruteforce,
)

router = APIRouter(prefix="/api")

AVATARS = [
    "avatar1.png", "avatar2.png", "avatar3.png", "avatar4.png", "avatar4.gif",
    "avatar5.gif", "avatar6.gif", "avatar7.gif", "avatar11.gif", "avatar12.gif",
    "avatar13.gif", "avatar14.gif", "avatar8.gif", "avatar9.gif", "avatar10.gif",
    "avatar15.gif", "avatar16.gif", "avatar17.gif",
]


@router.post("/login")
async def login(request: Request, response: Response):
    ip = get_real_ip(request)

    if await is_ip_blocked(ip):
        return JSONResponse(status_code=403, content={"success": False, "message": "IP временно заблокирован"})

    if await check_login_bruteforce(ip):
        await ban_ip(ip, "too many failed logins", hours=1)
        return JSONResponse(status_code=429, content={"success": False, "message": "Слишком много попыток. Попробуйте позже"})

    data = await request.json()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = await fetch_one("SELECT * FROM users WHERE username = ?", (username,))

    if user and bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        await record_login_attempt(ip, username, success=True)
        content = {"success": True, "user_id": user["id"], "username": user["username"]}
        json_resp = JSONResponse(content=content)
        # Простая кука с user_id. Для серьёзной защиты добавь подпись (itsdangerous)
        # или JWT — но для self-hosted сервера в локальной сети этого достаточно.
        json_resp.set_cookie(
            key="session_user_id",
            value=str(user["id"]),
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )
        return json_resp

    await record_login_attempt(ip, username, success=False)
    return JSONResponse(status_code=401, content={"success": False, "message": "Неверный логин или пароль"})


@router.post("/register")
async def register(request: Request):
    ip = get_real_ip(request)

    if await is_ip_blocked(ip):
        return JSONResponse(status_code=403, content={"success": False, "message": "IP временно заблокирован"})

    if not await check_registration_rate_limit(ip, limit_per_day=3):
        return JSONResponse(status_code=429, content={"success": False, "message": "Лимит регистраций с этого IP на сегодня исчерпан"})

    data = await request.json()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3 or len(password) < 4:
        return JSONResponse(status_code=400, content={"success": False, "message": "Слишком короткий логин или пароль"})
    if len(password.encode("utf-8")) > 72:
        return JSONResponse(status_code=400, content={"success": False, "message": "Пароль слишком длинный"})

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        await execute_query(
            "INSERT INTO users (username, password, avatar) VALUES (?, ?, ?)",
            (username, hashed, "avatar1.png"),
        )
        await increment_registration_ip(ip)
        return {"success": True, "message": "Аккаунт создан!"}
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "Логин занят"})


@router.get("/user/{user_id}/profile")
async def get_profile(user_id: int):
    user = await fetch_one(
        "SELECT id, username, avatar, description, is_premium, reg_date FROM users WHERE id = ?",
        (user_id,),
    )
    if user:
        return dict(user)
    raise HTTPException(status_code=404, detail="User not found")


@router.put("/user/{user_id}/profile")
async def update_profile(user_id: int, request: Request):
    data = await request.json()
    avatar = data.get("avatar")
    description = data.get("description", "")

    if avatar and avatar not in AVATARS:
        return JSONResponse(status_code=400, content={"success": False, "message": "Недопустимая аватарка"})

    await execute_query(
        "UPDATE users SET avatar = COALESCE(?, avatar), description = ? WHERE id = ?",
        (avatar, description, user_id),
    )
    return {"success": True, "message": "Профиль успешно обновлен"}


@router.get("/avatars")
async def get_avatars_list():
    return AVATARS
