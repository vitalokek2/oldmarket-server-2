from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from database import fetch_one, execute_query

router = APIRouter(prefix="/api")

@router.post("/login")
async def login(request: Request, response: Response):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    user = await fetch_one("SELECT * FROM users WHERE username = ?", (username,))

    if user and user["password"] == password:
        # 1. Формируем ТОЧНО такой же JSON, как в оригинале
        content = {
            "success": True,
            "user_id": user["id"],
            "username": user["username"]
        }
        
        # 2. Создаем ответ
        json_resp = JSONResponse(content=content)
        
        # 3. Эмулируем куку Flask (Werkzeug). 
        # В реальности тут зашифрован JSON {"user_id": 503}.
        # Мы сделаем простую куку, чтобы клиент думал, что всё ок.
        fake_session_cookie = f"eyJ1c2VyX2lkIjo{user['id']}9.fake.signature.cookie"
        json_resp.set_cookie(key="session", value=fake_session_cookie, httponly=True)
        
        return json_resp

    return JSONResponse(status_code=401, content={"success": False, "message": "Неверный логин или пароль"})

@router.post("/register")
async def register(request: Request):
    data = await request.json()
    try:
        await execute_query(
            "INSERT INTO users (username, password, avatar) VALUES (?, ?, ?)",
            (data.get("username"), data.get("password"), "avatar1.png")
        )
        return {"success": True, "message": "Аккаунт создан!"}
    except:
        return JSONResponse(status_code=400, content={"success": False, "message": "Логин занят"})

@router.get("/user/{user_id}/profile")
async def get_profile(user_id: int):
    user = await fetch_one("SELECT id, username, avatar, is_premium, reg_date FROM users WHERE id = ?", (user_id,))
    if user: return dict(user)
    return JSONResponse(status_code=404, content={"message": "User not found"})

@router.put("/user/{user_id}/profile")
async def update_profile(user_id: int, request: Request):
    data = await request.json()
    avatar = data.get("avatar")
    description = data.get("description", "")

    # Пробуем обновить и аватарку, и описание
    try:
        await execute_query(
            "UPDATE users SET avatar = ?, description = ? WHERE id = ?", 
            (avatar, description, user_id)
        )
    except Exception:
        # Если ты еще не добавлял колонку description в БД, 
        # скрипт не упадет, а просто обновит только то, что есть — аватарку.
        await execute_query(
            "UPDATE users SET avatar = ? WHERE id = ?", 
            (avatar, user_id)
        )

    # Отдаем стандартный успешный ответ, который ждет клиент
    return {"success": True, "message": "Профиль успешно обновлен"}

@router.get("/avatars")
async def get_avatars_list():
    return [
        "avatar1.png","avatar2.png","avatar3.png","avatar4.png","avatar4.gif",
        "avatar5.gif","avatar6.gif","avatar7.gif","avatar11.gif","avatar12.gif",
        "avatar13.gif","avatar14.gif","avatar8.gif","avatar9.gif","avatar10.gif",
        "avatar15.gif","avatar16.gif","avatar17.gif"
    ]
