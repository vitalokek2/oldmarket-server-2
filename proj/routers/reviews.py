import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from database import fetch_all, execute_query

router = APIRouter(prefix="/api")

# 1. Получение отзывов (GET /api/app/{app_id}/reviews)
@router.get("/app/{app_id}/reviews")
async def get_reviews(app_id: int):
    # Тянем отзывы из базы, сортируем: новые сверху
    query = "SELECT data FROM reviews WHERE app_id = ? ORDER BY id DESC"
    rows = await fetch_all(query, (app_id,))
    
    # Парсим JSON из колонки data
    reviews_list = []
    for row in rows:
        reviews_list.append(json.loads(row["data"]))
    
    return reviews_list

# 2. Публикация отзыва (POST /api/app/{app_id}/review)
@router.post("/app/{app_id}/review")
async def post_review(app_id: int, request: Request):
    try:
        data = await request.json()
        # Обычно клиент шлет: user_id, rating, comment
        user_id = data.get("user_id")
        rating = data.get("rating")
        comment = data.get("comment")
        
        if not user_id or rating is None:
            return JSONResponse(status_code=400, content={"success": False, "message": "Недостаточно данных"})

        # Подготавливаем объект JSON для колонки 'data', как это делает оригинал
        # (чтобы потом при GET всё отображалось красиво)
        review_object = {
            "user_id": user_id,
            "username": "vitalokek2", # В идеале тянуть из сессии/БД по user_id
            "rating": rating,
            "comment": comment,
            "date": "Только что" # Или сгенерировать дату
        }

        # Сохраняем в таблицу reviews
        query = """
            INSERT INTO reviews (app_id, user_id, rating, comment, data) 
            VALUES (?, ?, ?, ?, ?)
        """
        await execute_query(query, (
            app_id, 
            user_id, 
            rating, 
            comment, 
            json.dumps(review_object, ensure_ascii=False)
        ))

        return {"success": True, "message": "Отзыв опубликован!"}
    
    except Exception as e:
        print(f"Ошибка при сохранении отзыва: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка сервера"})
