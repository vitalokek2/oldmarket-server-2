import json
import os

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import FileResponse

from database import fetch_all, fetch_one, BASE_DIR
from security import get_real_ip, record_download_once

router = APIRouter(prefix="/api")
APKS_DIR = os.path.join(BASE_DIR, "downloaded", "apks")

# ============================================================
# ПРОДВИНУТЫЙ ПОИСК
# ============================================================

def _search_score(app: dict, query: str) -> int:
    q = query.lower()
    name = app.get("name", "").lower()
    author = app.get("author", "").lower()
    package = app.get("package", "").lower()
    category = app.get("category_code", "").lower()
    description = app.get("description", "").lower()
    tags = [str(t).lower() for t in app.get("tags", [])]

    if q in name: return 10
    if q in author: return 8
    if q in package: return 7
    if q in category: return 5
    if any(q in tag for tag in tags): return 4
    if q in description: return 2
    return 0


@router.get("/apps")
async def get_apps(is_game: int = Query(None), category: str = Query(None)):
    query = "SELECT data FROM apps WHERE 1=1"
    params = []
    if is_game is not None:
        query += " AND is_game = ?"
        params.append(is_game)
    if category is not None:
        query += " AND category_code = ?"
        params.append(category)
    rows = await fetch_all(query, tuple(params))
    return [json.loads(row["data"]) for row in rows]


@router.get("/apps/search")
async def search_apps(
    q: str = Query(..., description="Поисковый запрос"),
    category: str = Query(None, description="Фильтр по категории"),
    is_game: int = Query(None, description="0=приложения, 1=игры"),
    limit: int = Query(200),
    offset: int = Query(0),
):
    base_query = "SELECT data FROM apps WHERE 1=1"
    params = []

    if is_game is not None:
        base_query += " AND is_game = ?"
        params.append(is_game)
    if category is not None:
        base_query += " AND category_code = ?"
        params.append(category)

    rows = await fetch_all(base_query, tuple(params))
    all_apps = [json.loads(row["data"]) for row in rows]

    scored = []
    for app in all_apps:
        score = _search_score(app, q)
        if score > 0:
            scored.append((score, app))

    scored.sort(key=lambda x: (-x[0], -x[1].get("downloads", 0), x[1].get("name", "").lower()))
    results = [app for _, app in scored[offset:offset + limit]]
    return results


@router.get("/top-apps")
async def get_top_apps():
    rows = await fetch_all(
        "SELECT data FROM apps WHERE is_game = 0 "
        "ORDER BY CAST(json_extract(data, '$.downloads') AS INTEGER) DESC LIMIT 50"
    )
    return [json.loads(row["data"]) for row in rows]


@router.get("/top-games")
async def get_top_games():
    rows = await fetch_all(
        "SELECT data FROM apps WHERE is_game = 1 "
        "ORDER BY CAST(json_extract(data, '$.downloads') AS INTEGER) DESC LIMIT 50"
    )
    return [json.loads(row["data"]) for row in rows]


@router.get("/app/{app_id}")
async def get_app_detail(app_id: int):
    row = await fetch_one("SELECT data FROM apps WHERE id = ?", (app_id,))
    if not row:
        raise HTTPException(status_code=404)
    return json.loads(row["data"])


@router.get("/app/{app_id}/screenshots")
async def get_screenshots(app_id: int):
    row = await fetch_one("SELECT data FROM apps WHERE id = ?", (app_id,))
    if row:
        return json.loads(row["data"]).get("screenshots", [])
    return []


# ============================================================
# СКАЧИВАНИЕ — последняя и конкретная версия
# ============================================================

@router.get("/download/{app_id}")
async def download_apk_latest(app_id: int, request: Request):
    row = await fetch_one("SELECT data FROM apps WHERE id = ?", (app_id,))
    if not row:
        raise HTTPException(status_code=404)

    data = json.loads(row["data"])
    apk_name = data.get("apk_file")
    if not apk_name and data.get("versions"):
        apk_name = data["versions"][0].get("apk_file")

    if not apk_name:
        raise HTTPException(status_code=404, detail="APK not found")

    file_path = os.path.join(APKS_DIR, apk_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="APK file not found on disk")

    ip = get_real_ip(request)
    await record_download_once(app_id, ip)

    return FileResponse(
        path=file_path, filename=apk_name,
        media_type="application/vnd.android.package-archive"
    )


@router.get("/download/{app_id}/{version_code}")
async def download_apk_version(app_id: int, version_code: str, request: Request):
    row = await fetch_one("SELECT data FROM apps WHERE id = ?", (app_id,))
    if not row:
        raise HTTPException(status_code=404)

    data = json.loads(row["data"])
    versions = data.get("versions", [])

    target_version = None
    for v in versions:
        if str(v.get("version_code", "")) == str(version_code):
            target_version = v
            break

    if not target_version:
        raise HTTPException(status_code=404, detail=f"Version {version_code} not found")

    apk_name = target_version.get("apk_file")
    if not apk_name:
        raise HTTPException(status_code=404, detail="APK file not specified for this version")

    file_path = os.path.join(APKS_DIR, apk_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="APK file not found on disk")

    ip = get_real_ip(request)
    await record_download_once(app_id, ip)

    return FileResponse(
        path=file_path, filename=apk_name,
        media_type="application/vnd.android.package-archive"
    )
