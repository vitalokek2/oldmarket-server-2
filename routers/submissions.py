"""
Роутер для открытого добавления приложений.
Форма минимальна: APK + категория + описание.
Остальное (name, author, version, package, minSdk) извлекается из APK автоматически.
"""
import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

from database import fetch_all, fetch_one, execute_query, BASE_DIR
from config import get_limits

router = APIRouter()

UPLOAD_DIR = Path(BASE_DIR) / "downloaded" / "submissions"
APKS_DIR = Path(BASE_DIR) / "downloaded" / "apks"
ICONS_DIR = Path(BASE_DIR) / "downloaded" / "html" / "apps"
SCREENSHOTS_DIR = Path(BASE_DIR) / "downloaded" / "html" / "screenshots"
SITE_DIR = Path(BASE_DIR) / "site"

for d in [UPLOAD_DIR, APKS_DIR, ICONS_DIR, SCREENSHOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

CATEGORY_CHOICES = [
    ("system_utilites", "Системные утилиты"),
    ("video_hosting", "Видеохостинги"),
    ("social_network", "Социальные сети"),
    ("messenger", "Мессенджеры"),
    ("browsers", "Браузеры"),
    ("news", "Новости"),
    ("maps", "Карты"),
    ("bank", "Банки"),
    ("music", "Музыка"),
    ("music_players", "Аудиоплееры"),
    ("video_players", "Видеоплееры"),
    ("office", "Офис"),
    ("weather", "Погода"),
    ("vpn", "VPN"),
    ("personalization", "Персонализация"),
    ("education", "Обучение"),
    ("video_editor", "Видеоредакторы"),
    ("photo", "Фото"),
    ("launcher", "Лаунчеры"),
    ("emulators", "Эмуляторы"),
    ("keyboard", "Клавиатура"),
    ("screen_recorder", "Запись экрана"),
    ("clock", "Часы"),
    ("ai", "AI"),
    ("camera", "Камера"),
    ("disk", "Облако"),
    ("mail", "Почта"),
    ("others", "Другие"),
    ("simulators", "Симуляторы"),
    ("puzzles", "Головоломки"),
    ("arcade", "Аркада"),
    ("races", "Гонки"),
    ("action_games", "Экшен"),
    ("casual", "Казуальные"),
    ("strategies", "Стратегии"),
    ("table_games", "Настольные игры"),
    ("shooter", "Шутеры"),
    ("horror", "Хоррор"),
    ("adventures", "Приключения"),
    ("rpg", "РПГ"),
    ("survival", "Выживание"),
    ("sport", "Спорт"),
    ("card_games", "Карточные игры"),
    ("other_games", "Другие игры"),
]

APP_CATEGORIES = [c for c in CATEGORY_CHOICES if c[0] not in {
    "simulators", "puzzles", "arcade", "races", "action_games", "casual",
    "strategies", "table_games", "shooter", "horror", "adventures", "rpg",
    "survival", "sport", "card_games", "other_games"
}]

GAME_CATEGORIES = [c for c in CATEGORY_CHOICES if c[0] in {
    "simulators", "puzzles", "arcade", "races", "action_games", "casual",
    "strategies", "table_games", "shooter", "horror", "adventures", "rpg",
    "survival", "sport", "card_games", "other_games"
}]


def _guess_is_game(category_code: str) -> int:
    return 1 if category_code in {c[0] for c in GAME_CATEGORIES} else 0


def _save_upload(file: UploadFile, dest_dir: Path, prefix: str = "") -> str:
    ext = Path(file.filename or "file.bin").suffix.lower()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}{timestamp}_{os.urandom(4).hex()}{ext}"
    dest_path = dest_dir / filename
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return filename


# ============================================================
# ПАРСИНГ APK
# ============================================================

def _parse_apk_manifest(apk_path: Path) -> dict:
    result = {"package": "", "version_name": "", "version_code": "", "min_sdk": "", "app_name": ""}
    try:
        # --- 1. Парсим AndroidManifest.xml ---
        manifest_raw = None
        with zipfile.ZipFile(apk_path, 'r') as z:
            if 'AndroidManifest.xml' in z.namelist():
                manifest_raw = z.read('AndroidManifest.xml')

        if manifest_raw:
            # 1a. Пробуем aapt (самый надёжный)
            try:
                aapt_out = subprocess.run(
                    ['aapt', 'dump', 'badging', str(apk_path)],
                    capture_output=True, text=True, timeout=30
                )
                for line in aapt_out.stdout.split('\n'):
                    if line.startswith('package:'):
                        for part in line.split(' '):
                            if part.startswith('name='):
                                result["package"] = part.split('=')[1].strip("'\"")
                            elif part.startswith('versionCode='):
                                result["version_code"] = part.split('=')[1].strip("'\"")
                            elif part.startswith('versionName='):
                                result["version_name"] = part.split('=')[1].strip("'\"")
                    elif line.startswith('uses-sdk:'):
                        if 'minSdkVersion=' in line:
                            result["min_sdk"] = line.split("minSdkVersion=")[1].split()[0].strip("'\"")
                    elif line.startswith('application-label:'):
                        result["app_name"] = line.split(':', 1)[1].strip().strip("'\"")
            except FileNotFoundError:
                pass
            except subprocess.TimeoutExpired:
                print("aapt timed out")

            # 1b. Если aapt не дал package — парсим AXML вручную
            if not result["package"]:
                try:
                    from routers.axml_parser import parse_axml
                    parsed = parse_axml(manifest_raw)
                    for k in ("package", "version_code", "version_name", "min_sdk", "app_name"):
                        if not result[k]:
                            result[k] = parsed.get(k, "")
                except Exception as e:
                    print(f"AXML fallback error: {e}")

        # --- 2. Ищем иконку ---
        icon_paths = [
            # mipmap (Android 4.0+, API 14+)
            'res/mipmap-xxxhdpi-v4/ic_launcher.png',
            'res/mipmap-xxhdpi-v4/ic_launcher.png',
            'res/mipmap-xhdpi-v4/ic_launcher.png',
            'res/mipmap-hdpi-v4/ic_launcher.png',
            'res/mipmap-mdpi-v4/ic_launcher.png',
            # drawable (Android 1.0+, API 1+)
            'res/drawable-xxxhdpi-v4/ic_launcher.png',
            'res/drawable-xxhdpi-v4/ic_launcher.png',
            'res/drawable-xhdpi-v4/ic_launcher.png',
            'res/drawable-hdpi-v4/ic_launcher.png',
            'res/drawable-mdpi-v4/ic_launcher.png',
            'res/drawable-ldpi-v4/ic_launcher.png',
            'res/drawable-hdpi/ic_launcher.png',
            'res/drawable-mdpi/ic_launcher.png',
            'res/drawable-ldpi/ic_launcher.png',
            'res/drawable/ic_launcher.png',
        ]
        with zipfile.ZipFile(apk_path, 'r') as z:
            names = z.namelist()
            for ip in icon_paths:
                if ip in names:
                    result["icon_path"] = ip
                    break

            if not result.get("icon_path"):
                # Fallback: любой ic_launcher PNG
                for name in names:
                    if 'ic_launcher' in name and name.endswith('.png'):
                        result["icon_path"] = name
                        break

            if not result.get("icon_path"):
                # Fallback: любой ic_launcher XML (векторная иконка 5.0+)
                for name in names:
                    if 'ic_launcher' in name and name.endswith('.xml'):
                        result["icon_path"] = name
                        break

            if not result.get("icon_path"):
                # Fallback: первый PNG из mipmap/drawable
                for name in names:
                    if name.startswith('res/mipmap') and name.endswith('.png'):
                        result["icon_path"] = name
                        break
                if not result.get("icon_path"):
                    for name in names:
                        if name.startswith('res/drawable') and name.endswith('.png'):
                            result["icon_path"] = name
                            break
    except Exception as e:
        print(f"APK parse error: {e}")
    return result


def _extract_apk_icon(apk_path: Path, icon_path: str, dest_dir: Path) -> Optional[str]:
    try:
        with zipfile.ZipFile(apk_path, 'r') as z:
            if icon_path in z.namelist():
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"icon_{timestamp}_{os.urandom(4).hex()}.png"
                dest = dest_dir / filename
                with z.open(icon_path) as src, open(dest, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                return filename
    except Exception as e:
        print(f"Icon extract error: {e}")
    return None


# ============================================================
# HTML-страница (отдаём из site/submit.html)
# ============================================================

@router.get("/submit", response_class=HTMLResponse)
async def submission_form(request: Request):
    """Отдаёт HTML-форму из site/submit.html"""
    submit_path = SITE_DIR / "submit.html"
    if submit_path.exists():
        return HTMLResponse(content=submit_path.read_text(encoding="utf-8"))
    # Fallback если файл не найден
    return HTMLResponse(content="<h1>submit.html not found</h1>", status_code=404)


@router.post("/submit")
async def submit_app(
    request: Request,
    category: str = Form(...),
    description: str = Form(...),
    apk: UploadFile = File(...),
):
    """Принимает форму: только APK + категория + описание. Остальное из APK."""

    desc_clean = description.strip()
    if len(desc_clean) < 10:
        return _redirect_error("Описание слишком короткое (минимум 10 символов)")

    valid_cats = {c[0] for c in CATEGORY_CHOICES}
    if category not in valid_cats:
        return _redirect_error("Неверная категория")

    apk_ext = Path(apk.filename or "").suffix.lower()
    if apk_ext not in (".apk", ".xapk", ".apkm"):
        return _redirect_error("Файл должен быть .apk, .xapk или .apkm")

    # Проверка размера APK
    limits = get_limits()
    max_size = limits.get("max_apk_size_mb", 200) * 1024 * 1024
    apk_content = await apk.read()
    if len(apk_content) > max_size:
        return _redirect_error(f"APK слишком большой (максимум {limits.get('max_apk_size_mb', 200)} МБ)")

    # Сохраняем APK
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    apk_filename = f"apk_{timestamp}_{os.urandom(4).hex()}{apk_ext}"
    apk_path = UPLOAD_DIR / apk_filename
    with open(apk_path, "wb") as f:
        f.write(apk_content)

    # Парсим APK
    parsed = _parse_apk_manifest(apk_path)

    app_name = parsed.get("app_name") or parsed.get("package", "").split(".")[-1].replace("_", " ").title() or Path(apk.filename).stem
    package = parsed.get("package", "")
    author = package.split(".")[1] if len(package.split(".")) > 1 else "Unknown"

    icon_filename = None
    if parsed.get("icon_path"):
        icon_filename = _extract_apk_icon(apk_path, parsed["icon_path"], UPLOAD_DIR)

    submission_data = {
        "name": app_name,
        "author": author,
        "package": package,
        "category_code": category,
        "category_label": next((l for c, l in CATEGORY_CHOICES if c == category), category),
        "description": desc_clean,
        "version": parsed.get("version_name") or "1.0",
        "version_code": parsed.get("version_code") or "1",
        "min_android": parsed.get("min_sdk") or "",
        "apk_file": apk_filename,
        "icon": icon_filename or "",
        "screenshots": [],
        "submitted_at": datetime.utcnow().isoformat(),
        "status": "pending",
    }

    await execute_query(
        "INSERT INTO submissions (name, author, category_code, data) VALUES (?, ?, ?, ?)",
        (app_name, author, category, json.dumps(submission_data, ensure_ascii=False)),
    )

    return _redirect_success(f"Приложение «{app_name}» (v{submission_data['version']}) отправлено на модерацию!")


def _redirect_success(message: str):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/submit?msg={message}&type=success", status_code=303)


def _redirect_error(message: str):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/submit?msg={message}&type=error", status_code=303)


# ============================================================
# API для администрирования заявок
# ============================================================

@router.get("/api/submissions")
async def list_submissions(status: Optional[str] = None):
    if status:
        rows = await fetch_all(
            "SELECT * FROM submissions WHERE status = ? ORDER BY id DESC", (status,)
        )
    else:
        rows = await fetch_all("SELECT * FROM submissions ORDER BY id DESC")
    return [{
        "id": r["id"],
        "name": r["name"],
        "author": r["author"],
        "category_code": r["category_code"],
        "status": r["status"],
        "data": json.loads(r["data"]),
    } for r in rows]


@router.post("/api/submissions/{sub_id}/approve")
async def approve_submission(sub_id: int):
    row = await fetch_one("SELECT * FROM submissions WHERE id = ?", (sub_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail="Заявка уже обработана")

    data = json.loads(row["data"])
    max_id_row = await fetch_one("SELECT MAX(id) as max_id FROM apps")
    new_id = (max_id_row["max_id"] or 0) + 1

    apk_src = UPLOAD_DIR / data["apk_file"]
    apk_dest = APKS_DIR / data["apk_file"]
    if apk_src.exists():
        shutil.move(str(apk_src), str(apk_dest))

    icon_name = data.get("icon", "")
    if icon_name:
        icon_src = UPLOAD_DIR / icon_name
        icon_dest = ICONS_DIR / icon_name
        if icon_src.exists():
            shutil.move(str(icon_src), str(icon_dest))

    app_json = {
        "id": new_id,
        "name": data["name"],
        "author": data["author"],
        "package": data.get("package", ""),
        "description": data["description"],
        "version": data.get("version", "1.0"),
        "version_code": data.get("version_code", "1"),
        "apk_file": data["apk_file"],
        "icon": icon_name or "default_icon.png",
        "screenshots": data.get("screenshots", []),
        "category_code": data["category_code"],
        "category_label": data["category_label"],
        "is_game": _guess_is_game(data["category_code"]),
        "downloads": 0,
        "rating": 0.0,
        "review_count": 0,
    }

    if data.get("min_android"):
        app_json["api"] = data["min_android"]

    app_json["versions"] = [{
        "version_name": data.get("version", "1.0"),
        "version_code": data.get("version_code", "1"),
        "apk_file": data["apk_file"],
    }]

    await execute_query(
        "INSERT INTO apps (id, is_game, category_code, data) VALUES (?, ?, ?, ?)",
        (new_id, app_json["is_game"], data["category_code"],
         json.dumps(app_json, ensure_ascii=False)),
    )

    await execute_query(
        "UPDATE submissions SET status = 'approved' WHERE id = ?", (sub_id,),
    )

    return {"success": True, "app_id": new_id}


@router.post("/api/submissions/{sub_id}/reject")
async def reject_submission(sub_id: int, reason: Optional[str] = None):
    row = await fetch_one("SELECT * FROM submissions WHERE id = ?", (sub_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    data = json.loads(row["data"])
    data["reject_reason"] = reason or ""

    await execute_query(
        "UPDATE submissions SET status = 'rejected', data = ? WHERE id = ?",
        (json.dumps(data, ensure_ascii=False), sub_id),
    )

    return {"success": True}
