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
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from database import fetch_all, fetch_one, execute_query, BASE_DIR

router = APIRouter()

UPLOAD_DIR = Path(BASE_DIR) / "downloaded" / "submissions"
APKS_DIR = Path(BASE_DIR) / "downloaded" / "apks"
ICONS_DIR = Path(BASE_DIR) / "downloaded" / "html" / "apps"
SCREENSHOTS_DIR = Path(BASE_DIR) / "downloaded" / "html" / "screenshots"

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
    """
    Извлекает package, versionName, versionCode, minSdkVersion из AndroidManifest.xml
    внутри APK (это ZIP-архив).
    """
    result = {
        "package": "",
        "version_name": "",
        "version_code": "",
        "min_sdk": "",
        "app_name": "",
    }
    try:
        with zipfile.ZipFile(apk_path, 'r') as z:
            # AndroidManifest.xml
            if 'AndroidManifest.xml' in z.namelist():
                with z.open('AndroidManifest.xml') as mf:
                    # AXML — бинарный XML, попробуем простой парсинг через ElementTree
                    # (может не сработать для бинарного XML, тогда fallback на aapt)
                    try:
                        tree = ET.parse(mf)
                        root = tree.getroot()
                        ns = {'android': 'http://schemas.android.com/apk/res/android'}

                        result["package"] = root.get('package', '')
                        result["version_name"] = root.get('{http://schemas.android.com/apk/res/android}versionName', '')
                        result["version_code"] = root.get('{http://schemas.android.com/apk/res/android}versionCode', '')

                        uses_sdk = root.find('uses-sdk', ns)
                        if uses_sdk is not None:
                            result["min_sdk"] = uses_sdk.get('{http://schemas.android.com/apk/res/android}minSdkVersion', '')

                        app = root.find('application', ns)
                        if app is not None:
                            result["app_name"] = app.get('{http://schemas.android.com/apk/res/android}label', '')
                    except ET.ParseError:
                        pass  # Бинарный XML, попробуем aapt

            # Fallback: попробуем aapt (если установлен Android SDK)
            if not result["package"]:
                try:
                    aapt_out = subprocess.run(
                        ['aapt', 'dump', 'badging', str(apk_path)],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in aapt_out.stdout.split('\n'):
                        if line.startswith('package:'):
                            # package: name='com.example' versionCode='1' versionName='1.0'
                            parts = line.split(' ')
                            for part in parts:
                                if part.startswith('name='):
                                    result["package"] = part.split('=')[1].strip("'\"")
                                elif part.startswith('versionCode='):
                                    result["version_code"] = part.split('=')[1].strip("'\"")
                                elif part.startswith('versionName='):
                                    result["version_name"] = part.split('=')[1].strip("'\"")
                        elif line.startswith('uses-sdk:'):
                            # uses-sdk: minSdkVersion='21'
                            if 'minSdkVersion=' in line:
                                result["min_sdk"] = line.split("minSdkVersion=")[1].split()[0].strip("'\"")
                        elif line.startswith('application-label:'):
                            result["app_name"] = line.split(':', 1)[1].strip().strip("'\"")
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass

            # Извлечь иконку из APK если нет загруженной
            if 'res/mipmap-xxxhdpi-v4/ic_launcher.png' in z.namelist():
                result["icon_path"] = 'res/mipmap-xxxhdpi-v4/ic_launcher.png'
            elif 'res/mipmap-xxhdpi-v4/ic_launcher.png' in z.namelist():
                result["icon_path"] = 'res/mipmap-xxhdpi-v4/ic_launcher.png'
            elif 'res/mipmap-xhdpi-v4/ic_launcher.png' in z.namelist():
                result["icon_path"] = 'res/mipmap-xhdpi-v4/ic_launcher.png'
            elif 'res/mipmap-hdpi-v4/ic_launcher.png' in z.namelist():
                result["icon_path"] = 'res/mipmap-hdpi-v4/ic_launcher.png'
            elif 'res/mipmap-mdpi-v4/ic_launcher.png' in z.namelist():
                result["icon_path"] = 'res/mipmap-mdpi-v4/ic_launcher.png'
            else:
                # Ищем любую иконку
                for name in z.namelist():
                    if 'ic_launcher' in name and name.endswith('.png'):
                        result["icon_path"] = name
                        break

    except Exception as e:
        print(f"APK parse error: {e}")

    return result


def _extract_apk_icon(apk_path: Path, icon_path: str, dest_dir: Path) -> Optional[str]:
    """Извлекает иконку из APK и сохраняет в dest_dir."""
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
# HTML-форма (минимальная)
# ============================================================

HTML_FORM = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Добавить приложение — AltMart</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            color: #e0e0e0;
        }
        .container {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
        }
        h1 { text-align: center; margin-bottom: 10px; color: #fff; font-size: 24px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 14px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 500; color: #ccc; }
        input[type="file"], select, textarea {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            background: rgba(0,0,0,0.2);
            color: #fff;
            font-size: 15px;
            transition: all 0.3s;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #4a9eff;
            box-shadow: 0 0 0 3px rgba(74,158,255,0.1);
        }
        select option { background: #1a1a2e; color: #fff; }
        textarea { min-height: 120px; resize: vertical; }
        .file-hint { font-size: 12px; color: #666; margin-top: 5px; }
        .btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #4a9eff 0%, #357abd 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(74,158,255,0.4); }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .success { 
            background: rgba(46, 204, 113, 0.15); border: 1px solid #2ecc71; 
            color: #2ecc71; padding: 15px; border-radius: 12px; margin-bottom: 20px; text-align: center;
        }
        .error { 
            background: rgba(231, 76, 60, 0.15); border: 1px solid #e74c3c; 
            color: #e74c3c; padding: 15px; border-radius: 12px; margin-bottom: 20px; text-align: center;
        }
        .required { color: #e74c3c; }
        .parsed-info {
            background: rgba(74, 158, 255, 0.1);
            border: 1px solid rgba(74, 158, 255, 0.3);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #aaa;
        }
        .parsed-info strong { color: #4a9eff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 Добавить приложение</h1>
        <p class="subtitle">Загрузите APK — остальное мы извлечём автоматически</p>

        <div id="messageBox" style="display:none;"></div>

        <form method="post" action="/submit" enctype="multipart/form-data" id="submitForm">
            <div class="form-group">
                <label>APK файл <span class="required">*</span></label>
                <input type="file" name="apk" accept=".apk,.xapk,.apkm" required>
                <p class="file-hint">Максимум 200 МБ. Поддерживаются .apk, .xapk, .apkm</p>
            </div>

            <div class="form-group">
                <label>Категория <span class="required">*</span></label>
                <select name="category" required>
                    <option value="">Выберите категорию...</option>
                    <optgroup label="Приложения">
                        {app_options}
                    </optgroup>
                    <optgroup label="Игры">
                        {game_options}
                    </optgroup>
                </select>
            </div>

            <div class="form-group">
                <label>Описание <span class="required">*</span></label>
                <textarea name="description" required placeholder="Краткое описание функционала, особенностей..."></textarea>
            </div>

            <button type="submit" class="btn" id="submitBtn">Отправить на модерацию</button>
        </form>
    </div>
    <script>
        const form = document.getElementById('submitForm');
        const btn = document.getElementById('submitBtn');
        const msgBox = document.getElementById('messageBox');

        const params = new URLSearchParams(window.location.search);
        const msg = params.get('msg');
        const type = params.get('type');
        if (msg) {
            msgBox.textContent = decodeURIComponent(msg);
            msgBox.className = type === 'success' ? 'success' : 'error';
            msgBox.style.display = 'block';
        }

        form.addEventListener('submit', function() {
            btn.disabled = true;
            btn.textContent = 'Анализ APK и загрузка...';
        });
    </script>
</body>
</html>
"""


def _render_form(message: str = "", msg_type: str = "") -> str:
    app_opts = "\n".join([f'<option value="{c[0]}">{c[1]}</option>' for c in APP_CATEGORIES])
    game_opts = "\n".join([f'<option value="{c[0]}">{c[1]}</option>' for c in GAME_CATEGORIES])
    html = HTML_FORM.replace("{app_options}", app_opts).replace("{game_options}", game_opts)
    if message:
        html = html.replace(
            '<div id="messageBox" style="display:none;"></div>',
            f'<div class="{msg_type}">{message}</div>'
        )
    return html


@router.get("/submit", response_class=HTMLResponse)
async def submission_form(request: Request):
    return HTMLResponse(content=_render_form())


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
        return HTMLResponse(content=_render_form("Описание слишком короткое (минимум 10 символов)", "error"), status_code=400)

    valid_cats = {c[0] for c in CATEGORY_CHOICES}
    if category not in valid_cats:
        return HTMLResponse(content=_render_form("Неверная категория", "error"), status_code=400)

    apk_ext = Path(apk.filename or "").suffix.lower()
    if apk_ext not in (".apk", ".xapk", ".apkm"):
        return HTMLResponse(content=_render_form("Файл должен быть .apk, .xapk или .apkm", "error"), status_code=400)

    # Сохраняем APK
    apk_filename = _save_upload(apk, UPLOAD_DIR, "apk_")
    apk_path = UPLOAD_DIR / apk_filename

    # Парсим APK
    parsed = _parse_apk_manifest(apk_path)

    # Имя приложения: из APK или из имени файла
    app_name = parsed.get("app_name") or parsed.get("package", "").split(".")[-1].replace("_", " ").title() or Path(apk.filename).stem

    # Автор: из package (первая часть домена) или Unknown
    package = parsed.get("package", "")
    author = package.split(".")[1] if len(package.split(".")) > 1 else "Unknown"

    # Извлекаем иконку из APK
    icon_filename = None
    if parsed.get("icon_path"):
        icon_filename = _extract_apk_icon(apk_path, parsed["icon_path"], UPLOAD_DIR)

    # Сохраняем заявку
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

    return HTMLResponse(content=_render_form(
        f"Приложение «{app_name}» (v{submission_data['version']}) отправлено на модерацию! "
        f"Package: {package or 'не определён'}. Оно появится в каталоге после проверки.",
        "success"
    ))


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

    # Генерируем ID
    max_id_row = await fetch_one("SELECT MAX(id) as max_id FROM apps")
    new_id = (max_id_row["max_id"] or 0) + 1

    # Перемещаем APK
    apk_src = UPLOAD_DIR / data["apk_file"]
    apk_dest = APKS_DIR / data["apk_file"]
    if apk_src.exists():
        shutil.move(str(apk_src), str(apk_dest))

    # Перемещаем иконку
    icon_name = data.get("icon", "")
    if icon_name:
        icon_src = UPLOAD_DIR / icon_name
        icon_dest = ICONS_DIR / icon_name
        if icon_src.exists():
            shutil.move(str(icon_src), str(icon_dest))

    # Формируем JSON в формате OldMarket API
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

    # Система версий для скачивания конкретной версии
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
