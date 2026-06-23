from fastapi import APIRouter, Query
from database import fetch_all

router = APIRouter(prefix="/api")


@router.get("/categories")
async def get_categories(is_game: int = Query(None)):
    query = "SELECT DISTINCT category_code, json_extract(data, '$.category_label') as label FROM apps"
    params: tuple = ()
    if is_game is not None:
        query += " WHERE is_game = ?"
        params = (is_game,)
    rows = await fetch_all(query, params)
    return [{"code": r[0], "label": r[1]} for r in rows if r[0]]


@router.get("/client/latest")
async def get_latest_client():
    return {
        "notes_en": "Self-hosted Server is Running!",
        "notes_ru": "Твой личный сервер запущен и работает!",
        "update_url": "http://127.0.0.1:5000/apks/OldMarket2_3.apk",  # поменяй на свой IP/домен
        "version_code": 13,
        "version_name": "2.3",
    }
