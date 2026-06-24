import json
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from database import fetch_all, fetch_one, execute_query

router = APIRouter(prefix="/api")


@router.get("/app/{app_id}/reviews")
async def get_reviews(app_id: int):
    rows = await fetch_all(
        "SELECT id, data FROM reviews WHERE app_id = ? ORDER BY id DESC", (app_id,)
    )
    result = []
    for row in rows:
        review = json.loads(row["data"])
        review["id"] = row["id"]

        # reactions
        likes = await fetch_one(
            "SELECT COUNT(*) as cnt FROM review_reactions WHERE review_id = ? AND value = 1",
            (row["id"],),
        )
        dislikes = await fetch_one(
            "SELECT COUNT(*) as cnt FROM review_reactions WHERE review_id = ? AND value = -1",
            (row["id"],),
        )
        review["likes"] = likes["cnt"] if likes else 0
        review["dislikes"] = dislikes["cnt"] if dislikes else 0

        # comments
        crows = await fetch_all(
            "SELECT user_id, text, created_at FROM review_comments WHERE review_id = ? ORDER BY created_at ASC",
            (row["id"],),
        )
        review["comments"] = [
            {"user_id": c["user_id"], "text": c["text"], "created_at": c["created_at"]}
            for c in crows
        ]

        result.append(review)
    return result


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

        existing = await fetch_one(
            "SELECT id FROM reviews WHERE app_id = ? AND user_id = ?",
            (app_id, user_id)
        )
        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Вы уже оставляли отзыв на это приложение"}
            )

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

        avg_row = await fetch_one(
            "SELECT AVG(rating) as avg_rating FROM reviews WHERE app_id = ?", (app_id,)
        )
        if avg_row and avg_row["avg_rating"] is not None:
            await execute_query(
                "UPDATE apps SET data = json_set(data, '$.rating', ?) WHERE id = ?",
                (round(avg_row["avg_rating"], 1), app_id),
            )
            count_row = await fetch_one(
                "SELECT COUNT(*) as cnt FROM reviews WHERE app_id = ?", (app_id,)
            )
            await execute_query(
                "UPDATE apps SET data = json_set(data, '$.review_count', ?) WHERE id = ?",
                (count_row["cnt"], app_id),
            )

        return {"success": True, "message": "Отзыв опубликован!"}

    except Exception as e:
        print(f"Ошибка при сохранении отзыва: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})


@router.post("/app/{app_id}/review/{review_id}/reaction")
async def post_review_reaction(app_id: int, review_id: int, request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        value = data.get("value")

        if not user_id or value not in (1, -1):
            return JSONResponse(status_code=400, content={"success": False, "message": "Некорректные данные"})

        review = await fetch_one("SELECT id FROM reviews WHERE id = ? AND app_id = ?", (review_id, app_id))
        if not review:
            return JSONResponse(status_code=404, content={"success": False, "message": "Отзыв не найден"})

        try:
            await execute_query(
                "INSERT INTO review_reactions (review_id, user_id, value, created_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(review_id, user_id) DO UPDATE SET value = excluded.value, created_at = excluded.created_at",
                (review_id, user_id, value, datetime.utcnow().isoformat()),
            )
        except Exception:
            return JSONResponse(status_code=400, content={"success": False, "message": "Ошибка сохранения реакции"})

        return {"success": True, "message": "Реакция сохранена"}

    except Exception as e:
        print(f"Ошибка реакции: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})


@router.get("/app/{app_id}/review/{review_id}/comments")
async def get_review_comments(app_id: int, review_id: int):
    review = await fetch_one("SELECT id FROM reviews WHERE id = ? AND app_id = ?", (review_id, app_id))
    if not review:
        return JSONResponse(status_code=404, content={"error": "Review not found"})

    rows = await fetch_all(
        """SELECT c.id, c.user_id, c.text, c.created_at, u.username
           FROM review_comments c
           LEFT JOIN users u ON u.id = c.user_id
           WHERE c.review_id = ?
           ORDER BY c.created_at ASC""",
        (review_id,),
    )
    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "username": r["username"] or "deleted",
            "text": r["text"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("/app/{app_id}/review/{review_id}/comment")
async def post_review_comment(app_id: int, review_id: int, request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        text = (data.get("text") or "").strip()

        if not user_id or not text:
            return JSONResponse(status_code=400, content={"success": False, "message": "Некорректные данные"})

        review = await fetch_one("SELECT id FROM reviews WHERE id = ? AND app_id = ?", (review_id, app_id))
        if not review:
            return JSONResponse(status_code=404, content={"success": False, "message": "Отзыв не найден"})

        await execute_query(
            "INSERT INTO review_comments (review_id, user_id, text, created_at) VALUES (?, ?, ?, ?)",
            (review_id, user_id, text, datetime.utcnow().isoformat()),
        )

        return {"success": True, "message": "Комментарий добавлен"}

    except Exception as e:
        print(f"Ошибка комментария: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})


@router.post("/app/{app_id}/review/{review_id}/report")
async def post_review_report(app_id: int, review_id: int, request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        reason = (data.get("reason") or "").strip()

        if not user_id:
            return JSONResponse(status_code=400, content={"success": False, "message": "user_id обязателен"})

        review = await fetch_one("SELECT id FROM reviews WHERE id = ? AND app_id = ?", (review_id, app_id))
        if not review:
            return JSONResponse(status_code=404, content={"success": False, "message": "Отзыв не найден"})

        await execute_query(
            "INSERT INTO review_reports (review_id, user_id, reason, status, created_at) VALUES (?, ?, ?, 'new', ?)",
            (review_id, user_id, reason, datetime.utcnow().isoformat()),
        )

        return {"success": True, "message": "Жалоба отправлена"}

    except Exception as e:
        print(f"Ошибка жалобы: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})
