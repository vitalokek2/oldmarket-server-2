import os
import hmac
import json
import shutil
import runpy
import zipfile
from io import BytesIO
from uuid import uuid4
from datetime import timedelta
from typing import List, Dict, Any, Optional

from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, abort, flash, send_from_directory
)

from androguard.core.apk import APK
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APPS_FILE = os.environ.get("APPS_FILE", os.path.join(BASE_DIR, "apps_data.py"))
BACKUP_FILE = os.environ.get("APPS_FILE_BAK", os.path.join(BASE_DIR, "apps_data.py.bak"))

FILES_UPLOAD_DIR = os.environ.get("FILES_UPLOAD_DIR", os.path.join(BASE_DIR, "html", "apps"))
os.makedirs(FILES_UPLOAD_DIR, exist_ok=True)

SCREENSHOTS_UPLOAD_DIR = os.environ.get("SCREENSHOTS_UPLOAD_DIR", os.path.join(BASE_DIR, "html", "screenshots"))
os.makedirs(SCREENSHOTS_UPLOAD_DIR, exist_ok=True)

SCREENSHOTS_BASE_URL = os.environ.get("SCREENSHOTS_BASE_URL", "http://94.156.115.120:5000/html/screenshots/")

MAX_CONTENT_LENGTH_MB = int(os.environ.get("MAX_CONTENT_LENGTH_MB", "200"))
ALLOWED_APK_EXT = {".apk", ".xapk", ".apkm"}
ALLOWED_ICON_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_SCREENSHOT_EXT = {".png", ".jpg", ".jpeg", ".webp"}

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD не задан. Установите переменную окружения ADMIN_PASSWORD.")

ALLOWED_IPS = set(filter(None, [ip.strip() for ip in os.environ.get("ALLOWED_IPS", "").split(",")]))
SECRET_KEY = os.environ.get("SECRET_KEY", "")
SESSION_LIFETIME_MIN = int(os.environ.get("SESSION_LIFETIME_MIN", "120"))

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=SESSION_LIFETIME_MIN)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH_MB * 1024 * 1024


@app.context_processor
def inject_common():
    try:
        ip = client_ip()
    except Exception:
        ip = ""
    return {
        "client_ip_str": ip,
        "allowed_ips": ALLOWED_IPS,
    }


def client_ip() -> str:
    return request.remote_addr or ""


def ip_allowed() -> bool:
    return client_ip() in ALLOWED_IPS


def load_apps() -> List[Dict[str, Any]]:
    ns = runpy.run_path(APPS_FILE)
    apps = ns.get("apps", [])
    if not isinstance(apps, list):
        raise RuntimeError("apps в apps_data.py должен быть списком.")
    return apps


def dump_python_literal(obj: Any) -> str:
    txt = json.dumps(obj, ensure_ascii=False, indent=4)
    txt = txt.replace("true", "True").replace("false", "False").replace("null", "None")
    return txt


def save_apps(apps: List[Dict[str, Any]]) -> None:
    if not isinstance(apps, list):
        raise RuntimeError("apps должен быть списком.")
    if os.path.exists(APPS_FILE):
        shutil.copyfile(APPS_FILE, BACKUP_FILE)
    body = "# -*- coding: utf-8 -*-\n# Файл сгенерирован админкой. Не редактируйте руками во время работы сервера.\napps = "
    body += dump_python_literal(apps) + "\n"
    with open(APPS_FILE, "w", encoding="utf-8") as f:
        f.write(body)



def _guess_archive_kind(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in ALLOWED_APK_EXT:
        return ext
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = [n.replace("\\", "/") for n in zf.namelist()]
            low_names = [n.lower() for n in names]
            if "androidmanifest.xml" in low_names:
                return ".apk"
            if any(n.endswith("/androidmanifest.xml") for n in low_names):
                return ".apk"
            if any(n.endswith(".apk") for n in low_names):
                return ".xapk"
    except Exception:
        pass
    return ext


def _save_uploaded(file_storage, allowed_ext: set, target_dir: str = None) -> str:
    if not file_storage or not getattr(file_storage, "filename", ""):
        return ""
    if not target_dir:
        target_dir = FILES_UPLOAD_DIR
    os.makedirs(target_dir, exist_ok=True)

    orig_name = os.path.basename(file_storage.filename)
    ext = os.path.splitext(orig_name)[1].lower()

    if ext not in allowed_ext:
        if allowed_ext == ALLOWED_APK_EXT:
            tmp_name = secure_filename(orig_name) or ("upload_" + uuid4().hex)
            tmp_path = os.path.join(target_dir, tmp_name)
            file_storage.save(tmp_path)
            guessed = _guess_archive_kind(tmp_path)
            if guessed in allowed_ext:
                base_name = os.path.splitext(tmp_name)[0] or ("upload_" + uuid4().hex)
                candidate = base_name + guessed
                idx = 1
                while os.path.exists(os.path.join(target_dir, candidate)):
                    candidate = f"{base_name}_{idx}{guessed}"
                    idx += 1
                final_path = os.path.join(target_dir, candidate)
                if tmp_path != final_path:
                    os.replace(tmp_path, final_path)
                return candidate
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise ValueError(f"Неподдерживаемый формат: {ext or 'без расширения'}")

    safe_name = secure_filename(orig_name)
    if not safe_name:
        raise ValueError("Некорректное имя файла")
    base_name, ext = os.path.splitext(safe_name)
    candidate = safe_name
    idx = 1
    while os.path.exists(os.path.join(target_dir, candidate)):
        candidate = f"{base_name}_{idx}{ext}"
        idx += 1
    target_path = os.path.join(target_dir, candidate)
    file_storage.save(target_path)
    return candidate


def find_app(apps: List[Dict[str, Any]], app_id: int) -> Optional[Dict[str, Any]]:
    return next((a for a in apps if int(a.get("id")) == int(app_id)), None)


def all_categories(apps: List[Dict[str, Any]]) -> List[str]:
    values = set()
    for a in apps:
        for key in ("category_label", "category", "category_code"):
            val = a.get(key)
            if isinstance(val, str) and val.strip():
                values.add(val.strip())
                break
    return sorted(values, key=lambda x: x.lower())


def normalize_form_item(form: Dict[str, Any], existing_item: Dict[str, Any] = None) -> Dict[str, Any]:
    raw_id = form.get("id")
    if raw_id is None or str(raw_id).strip() == "":
        if existing_item is not None:
            item_id = int(existing_item.get("id") or 0)
        else:
            item_id = 0
    else:
        try:
            item_id = int(raw_id)
        except Exception:
            if existing_item is not None:
                item_id = int(existing_item.get("id") or 0)
            else:
                item_id = 0

    return {
        "id": item_id,
        "name": form.get("name", "").strip(),
        "author": form.get("author", "").strip(),
        "category": form.get("category", "").strip(),
        "description": form.get("description", "").strip(),
        "version": form.get("version", "").strip(),
        "apk_file": form.get("apk_file", "").strip(),
        "icon": form.get("icon", "").strip(),
        "api": form.get("api", "").strip(),
        "package": form.get("package", "").strip(),
        "is_game": form.get("is_game") == "on",
    }


def _maybe_extract_base_apk(bundle_path: str) -> str:
    kind = _guess_archive_kind(bundle_path)

    if kind == ".apk":
        try:
            with zipfile.ZipFile(bundle_path, "r") as zf:
                names = [n.lower() for n in zf.namelist()]
                if "androidmanifest.xml" in names or any(n.endswith("/androidmanifest.xml") for n in names):
                    return bundle_path
        except Exception:
            pass

    if kind not in {".xapk", ".apkm", ".apk"}:
        raise ValueError(f"Неподдерживаемый формат: {kind or 'неизвестный'}")

    out_dir = bundle_path + "_unzipped"
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(bundle_path, "r") as zf:
        zf.extractall(out_dir)

    apks = []
    for root, _, files in os.walk(out_dir):
        for fn in files:
            if fn.lower().endswith(".apk"):
                apks.append(os.path.join(root, fn))

    if kind == ".apk" and not apks:
        return bundle_path

    if not apks:
        raise ValueError("В архиве xapk/apkm не найдено ни одного .apk файла.")

    for p in apks:
        if os.path.basename(p).lower() == "base.apk":
            return p
    base_like = [p for p in apks if "base" in os.path.basename(p).lower()]
    if base_like:
        return sorted(base_like, key=lambda x: os.path.getsize(x), reverse=True)[0]
    return sorted(apks, key=lambda x: os.path.getsize(x), reverse=True)[0]


def _save_icon_bytes_as_png(icon_bytes: bytes) -> str:
    img = Image.open(BytesIO(icon_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    unique_name = f"{uuid4().hex}_icon.png"
    target_path = os.path.join(FILES_UPLOAD_DIR, unique_name)
    img.save(target_path, format="PNG")
    return unique_name


def parse_app_from_bundle(saved_bundle_filename: str) -> Dict[str, str]:
    bundle_path = os.path.join(FILES_UPLOAD_DIR, saved_bundle_filename)
    apk_path = _maybe_extract_base_apk(bundle_path)
    a = APK(apk_path)
    package = a.get_package() or ""
    version = a.get_androidversion_name() or ""
    min_sdk = ""
    try:
        ms = a.get_min_sdk_version()
        if ms is not None:
            min_sdk = str(ms)
    except Exception:
        min_sdk = ""
    try:
        name = a.get_app_name() or ""
    except Exception:
        name = ""
    icon_filename = ""
    try:
        icon_path = a.get_app_icon()
        if icon_path:
            icon_bytes = a.get_file(icon_path)
            if icon_bytes:
                icon_filename = _save_icon_bytes_as_png(icon_bytes)
    except Exception:
        icon_filename = ""
    return {
        "name": name,
        "package": package,
        "version": version,
        "api": min_sdk,
        "icon_filename": icon_filename,
    }


def parse_versions_from_request() -> List[Dict[str, str]]:
    versions = []
    version_names = request.form.getlist("version_name[]")
    version_apis = request.form.getlist("version_api[]")
    version_apk_files = request.form.getlist("version_apk_file[]")
    version_uploads = request.files.getlist("version_apk_upload[]")
    row_count = max(len(version_names), len(version_apis), len(version_apk_files), len(version_uploads))
    for i in range(row_count):
        v_name = version_names[i].strip() if i < len(version_names) and version_names[i] else ""
        v_api = version_apis[i].strip() if i < len(version_apis) and version_apis[i] else ""
        v_apk = version_apk_files[i].strip() if i < len(version_apk_files) and version_apk_files[i] else ""
        v_upload = version_uploads[i] if i < len(version_uploads) else None
        if v_upload and getattr(v_upload, "filename", ""):
            v_apk = _save_uploaded(v_upload, ALLOWED_APK_EXT)
        if not v_name and not v_api and not v_apk:
            continue
        if not v_name:
            raise ValueError(f"У версии №{i+1} не указано поле version.")
        versions.append({
            "version": v_name,
            "apk_file": v_apk,
            "api": v_api,
        })
    return versions


def parse_screenshots_from_request(existing_item: Optional[Dict[str, Any]] = None) -> List[str]:
    keep = request.form.getlist("keep_screenshots")
    screenshots = [x.strip() for x in keep if x.strip()]
    for fs in request.files.getlist("screenshots_upload"):
        if fs and getattr(fs, "filename", ""):
            screenshots.append(_save_uploaded(fs, ALLOWED_SCREENSHOT_EXT, SCREENSHOTS_UPLOAD_DIR))
    return screenshots


def prepare_versions_for_form(item: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows = item.get("versions", []) if item else []
    prepared = []
    for row in rows:
        prepared.append({
            "version": row.get("version", ""),
            "apk_file": row.get("apk_file", ""),
            "api": row.get("api", ""),
        })
    if not prepared:
        prepared = [{"version": "", "apk_file": "", "api": ""}]
    return prepared


@app.before_request
def _restrict():
    open_paths = {"/login"}
    if request.path in open_paths or request.path.startswith("/static/"):
        return
    if not ip_allowed():
        abort(403)
    if request.endpoint != "login" and not session.get("auth_ok"):
        return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session.permanent = True
            session["auth_ok"] = True
            flash("Вход выполнен", "success")
            return redirect(request.args.get("next") or url_for("index"))
        flash("Неверный пароль", "danger")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Вы вышли из системы", "info")
    return redirect(url_for("login"))


@app.route("/")
def index():
    apps = load_apps()
    q = (request.args.get("q") or "").strip().lower()
    app_type = (request.args.get("type") or "").strip().lower()
    category = (request.args.get("category") or "").strip()

    filtered = []
    for a in apps:
        is_game = bool(a.get("is_game"))
        if app_type == "apps" and is_game:
            continue
        if app_type == "games" and not is_game:
            continue
        if category:
            cat_value = str(a.get("category") or a.get("category_label") or a.get("category_code") or "").strip()
            if cat_value != category:
                continue
        if q:
            hay = " ".join([
                str(a.get("name", "")),
                str(a.get("author", "")),
                str(a.get("package", "")),
                str(a.get("category", "")),
                str(a.get("description", "")),
                str(a.get("version", "")),
            ]).lower()
            if q not in hay:
                continue
        filtered.append(a)

    apps_sorted = sorted(filtered, key=lambda x: int(x.get("id", 0)))
    categories = all_categories(apps)
    return render_template("index.html", apps=apps_sorted, q=q, app_type=app_type, category=category, categories=categories)

@app.route("/parse_apk", methods=["POST"])
def parse_apk_endpoint():
    if not ip_allowed():
        abort(403)
    if not session.get("auth_ok"):
        abort(401)
    apk_fs = request.files.get("apk_upload")
    if not apk_fs or not apk_fs.filename:
        return {"ok": False, "error": "Файл не выбран"}, 400
    try:
        saved_name = _save_uploaded(apk_fs, ALLOWED_APK_EXT)
        meta = parse_app_from_bundle(saved_name)
        resp_meta = {
            "name": meta.get("name", ""),
            "package": meta.get("package", ""),
            "version": meta.get("version", ""),
            "api": meta.get("api", ""),
            "icon": meta.get("icon_filename", ""),
            "icon_url": ("/files/" + meta.get("icon_filename", "")) if meta.get("icon_filename", "") else "",
        }
        return {"ok": True, "filename": saved_name, "meta": resp_meta}
    except Exception as e:
        return {"ok": False, "error": str(e) or "Не удалось обработать APK/XAPK/APKM"}, 400


@app.route("/new", methods=["GET", "POST"])
def new_app():
    apps = load_apps()
    categories = all_categories(apps)
    if request.method == "POST":
        form = dict(request.form)
        try:
            new_item = normalize_form_item(form, None)
            apk_fs = request.files.get("apk_upload")
            icon_fs = request.files.get("icon_upload")
            parsed_meta = {}

            if apk_fs and apk_fs.filename:
                new_item["apk_file"] = _save_uploaded(apk_fs, ALLOWED_APK_EXT)
                try:
                    parsed_meta = parse_app_from_bundle(new_item["apk_file"])
                except Exception as e:
                    flash(f"Не удалось распарсить APK: {e}", "warning")
                    parsed_meta = {}

            if icon_fs and icon_fs.filename:
                new_item["icon"] = _save_uploaded(icon_fs, ALLOWED_ICON_EXT)
            elif (not new_item["icon"]) and parsed_meta.get("icon_filename"):
                new_item["icon"] = parsed_meta["icon_filename"]

            if not new_item["name"] and parsed_meta.get("name"):
                new_item["name"] = parsed_meta["name"]
            if not new_item["package"] and parsed_meta.get("package"):
                new_item["package"] = parsed_meta["package"]
            if not new_item["version"] and parsed_meta.get("version"):
                new_item["version"] = parsed_meta["version"]
            if not new_item["api"] and parsed_meta.get("api"):
                new_item["api"] = parsed_meta["api"]

            screenshots = parse_screenshots_from_request()
            versions = parse_versions_from_request()

            if screenshots:
                new_item["screenshots"] = screenshots
            if versions:
                new_item["versions"] = versions

            if not new_item["name"]:
                raise ValueError("name обязателен.")
            if not new_item["id"]:
                max_id = 0
                for a in apps:
                    try:
                        cur = int(a.get("id") or 0)
                    except Exception:
                        cur = 0
                    if cur > max_id:
                        max_id = cur
                new_item["id"] = max_id + 1
            if find_app(apps, new_item["id"]):
                raise ValueError(f"Приложение с id={new_item['id']} уже существует.")

            apps.append(new_item)
            save_apps(apps)
            flash("Приложение добавлено", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Ошибка: {e}", "danger")

    return render_template("edit.html", item=None, categories=categories, version_rows=prepare_versions_for_form(None))


@app.route("/files/<path:filename>")
def files_download(filename):
    full_path = os.path.join(FILES_UPLOAD_DIR, filename)
    if not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(FILES_UPLOAD_DIR, filename)


def screenshot_public_url(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    if name.startswith("http://") or name.startswith("https://"):
        return name
    base = SCREENSHOTS_BASE_URL
    if not base.endswith("/"):
        base += "/"
    return base + name


@app.route("/edit/<int:app_id>", methods=["GET", "POST"])
def edit_app(app_id: int):
    apps = load_apps()
    categories = all_categories(apps)
    item = find_app(apps, app_id)
    if not item:
        abort(404)

    if request.method == "POST":
        try:
            old_id = int(item.get("id") or app_id)
            form = dict(request.form)
            item.update(normalize_form_item(form, item))
            item["id"] = old_id
            apk_fs = request.files.get("apk_upload")
            icon_fs = request.files.get("icon_upload")
            parsed_meta = {}

            if apk_fs and apk_fs.filename:
                item["apk_file"] = _save_uploaded(apk_fs, ALLOWED_APK_EXT)
                try:
                    parsed_meta = parse_app_from_bundle(item["apk_file"])
                except Exception as e:
                    flash(f"Не удалось распарсить APK: {e}", "warning")
                    parsed_meta = {}

            if icon_fs and icon_fs.filename:
                item["icon"] = _save_uploaded(icon_fs, ALLOWED_ICON_EXT)
            elif (not item.get("icon")) and parsed_meta.get("icon_filename"):
                item["icon"] = parsed_meta["icon_filename"]

            if (not item.get("name")) and parsed_meta.get("name"):
                item["name"] = parsed_meta["name"]
            if (not item.get("package")) and parsed_meta.get("package"):
                item["package"] = parsed_meta["package"]
            if (not item.get("version")) and parsed_meta.get("version"):
                item["version"] = parsed_meta["version"]
            if (not item.get("api")) and parsed_meta.get("api"):
                item["api"] = parsed_meta["api"]

            screenshots = parse_screenshots_from_request(item)
            versions = parse_versions_from_request()

            if screenshots:
                item["screenshots"] = screenshots
            else:
                item.pop("screenshots", None)

            if versions:
                item["versions"] = versions
            else:
                item.pop("versions", None)

            save_apps(apps)
            flash("Изменения сохранены", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Ошибка: {e}", "danger")

    return render_template("edit.html", item=item, categories=categories, version_rows=prepare_versions_for_form(item))


@app.route("/delete/<int:app_id>", methods=["POST"])
def delete_app(app_id: int):
    apps = load_apps()
    item = find_app(apps, app_id)
    if not item:
        abort(404)
    apps = [a for a in apps if int(a.get("id")) != int(app_id)]
    save_apps(apps)
    flash(f"Удалено приложение id={app_id}", "warning")
    return redirect(url_for("index"))


if __name__ == "__main__":
    print(f"[admin] ALLOWED_IPS: {', '.join(ALLOWED_IPS)}")
    print("[admin] Используйте переменные окружения: ADMIN_PASSWORD, ALLOWED_IPS, SECRET_KEY")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
