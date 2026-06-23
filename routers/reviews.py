import json
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from database import fetch_all, fetch_one, execute_query

router = APIRouter(prefix="/api")


@router.get("/app/{app_id}/reviews")
async def get_reviews(app_id: int):
    rows = await fetch_all(
        "SELECT data FROM reviews WHERE app_id = ? ORDER BY id DESC", (app_id,)
    )
    return [json.loads(row["data"]) for row in rows]


@router.post("/app/{app_id}/review")
async def post_review(app_id: int, request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        rating = data.get("rating")
        comment = (data.get("comment") or "").strip()

        if not user_id or rating is None:
            return JSONResponse(status_code=400, content={"success": False, "message": "Недостаточно данных"})

        if not (1 <= int(rating) <= 5):
            return JSONResponse(status_code=400, content={"success": False, "message": "Оценка должна быть от 1 до 5"})

        user = await fetch_one("SELECT username FROM users WHERE id = ?", (user_id,))
        if not user:
            return JSONResponse(status_code=404, content={"success": False, "message": "Пользователь не найден"})

        review_object = {
            "user_id": user_id,
            "username": user["username"],
            "rating": rating,
            "comment": comment,
            "date": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }

        await execute_query(
            "INSERT INTO reviews (app_id, user_id, rating, comment, data) VALUES (?, ?, ?, ?, ?)",
            (app_id, user_id, rating, comment, json.dumps(review_object, ensure_ascii=False)),
        )

        # Пересчитываем средний рейтинг приложения, как делал оригинал
        avg_row = await fetch_one(
            "SELECT AVG(rating) as avg_rating FROM reviews WHERE app_id = ?", (app_id,)
        )
        if avg_row and avg_row["avg_rating"] is not None:
            await execute_query(
                "UPDATE apps SET data = json_set(data, '$.rating', ?) WHERE id = ?",
                (round(avg_row["avg_rating"], 1), app_id),
            )

        return {"success": True, "message": "Отзыв опубликован!"}

    except Exception as e:
        print(f"Ошибка при сохранении отзыва: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})
