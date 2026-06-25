import os, re, json, shutil, hmac
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4
from io import BytesIO

from fastapi import FastAPI, Request, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, func, select, delete, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pydantic import BaseModel

from apps_data import apps
from site_config import SITE, LINKS, BANNER_LINKS, CDN, cdn_url, ADMIN as ADMIN_CFG, apply_config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "html", "apps")
BANNERS_DIR = os.path.join(BASE_DIR, "html", "banners")
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "html", "screenshots")
AVATARS_DIR = os.path.join(BASE_DIR, "html", "avatars")

DB_PATH = os.path.join(BASE_DIR, "oldmarket.db")
APPS_FILE = os.path.join(BASE_DIR, "apps_data.py")
APPS_BACKUP = os.path.join(BASE_DIR, "apps_data.py.bak")

CATEGORY_CHOICES = {
    "system_utilites": "Системные утилиты", "video_hosting": "Видеохостинги",
    "social_network": "Социальные сети", "messenger": "Мессенджеры",
    "browsers": "Браузеры", "news": "Новости", "maps": "Карты", "bank": "Банки",
    "music": "Музыка", "music_players": "Аудиоплееры", "video_players": "Видеоплееры",
    "office": "Офис", "weather": "Погода", "vpn": "VPN",
    "personalization": "Персонализация", "education": "Обучение",
    "video_editor": "Видеоредакторы", "photo": "Фото", "launcher": "Лаунчеры",
    "emulators": "Эмуляторы", "keyboard": "Клавиатура",
    "screen_recorder": "Запись экрана", "clock": "Часы", "ai": "AI",
    "camera": "Камера", "disk": "Облако", "mail": "Почта",
    "notworked": "Не рабочие(для красоты)", "others": "Другие",
    "simulators": "Симуляторы", "puzzles": "Головоломки", "arcade": "Аркада",
    "races": "Гонки", "action_games": "Экшен", "casual": "Казуальные",
    "strategies": "Стратегии", "table_games": "Настольные игры",
    "shooter": "Шутеры", "horror": "Хоррор", "adventures": "Приключения",
    "rpg": "РПГ", "survival": "Выживание", "sport": "Спорт",
    "card_games": "Карточные игры", "other_games": "Другие игры",
}

API_MAP = {1:"Android 1.0",2:"Android 1.1",3:"Android 1.5",4:"Android 1.6",5:"Android 2.0",
           6:"Android 2.0.1",7:"Android 2.1",8:"Android 2.2",9:"Android 2.3",10:"Android 2.3.3",
           11:"Android 3.0",12:"Android 3.1",13:"Android 3.2",14:"Android 4.0",15:"Android 4.0.3",
           16:"Android 4.1",17:"Android 4.2",18:"Android 4.3",19:"Android 4.4",20:"Android 4.4W"}

def api_level_to_android(api):
    try: return API_MAP.get(int(api), f"API {api}")
    except: return f"API {api}"

def cat_code(app):
    for k in ("category_code","category","genre_code","genre"):
        v = app.get(k)
        if isinstance(v, str) and v.strip(): return v.strip()
    return ""

def cat_label(code):
    return CATEGORY_CHOICES.get(code, code)

ALLOWED_APK_EXT = {".apk", ".xapk", ".apkm"}
ALLOWED_ICON_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_SCREENSHOT_EXT = {".png", ".jpg", ".jpeg", ".webp"}

# ─── DATABASE ───────────────────────────────────────────────────────────────

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"timeout": 30})
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_ip: Mapped[str] = mapped_column(String(50), nullable=True)

class Review(Base):
    __tablename__ = "review"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class ReviewReaction(Base):
    __tablename__ = "review_reaction"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class ReviewComment(Base):
    __tablename__ = "review_comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class Download(Base):
    __tablename__ = "download"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class DownloadIP(Base):
    __tablename__ = "download_ip"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ip: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class UserProfile(Base):
    __tablename__ = "user_profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    avatar: Mapped[str] = mapped_column(String(100), default="avatar1.png")
    description: Mapped[str] = mapped_column(Text, default="")
    is_premium: Mapped[int] = mapped_column(Integer, default=0)

class LoginAttempt(Base):
    __tablename__ = "login_attempt"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(80), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class BlockedIP(Base):
    __tablename__ = "blocked_ip"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    until: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class SecurityEvent(Base):
    __tablename__ = "security_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class Report(Base):
    __tablename__ = "report"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    reporter_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

Base.metadata.create_all(engine)

# ─── APP SETUP ───────────────────────────────────────────────────────────────

app = FastAPI(title=SITE["name"], version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/html", StaticFiles(directory=os.path.join(BASE_DIR, "html")), name="html")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
apply_config(templates)

@app.middleware("http")
async def lang_middleware(request: Request, call_next):
    """?lang=ru или ?lang=en — сохраняет в cookie и убирает из URL."""
    qlang = request.query_params.get("lang")
    if qlang in ("ru", "en"):
        resp = await call_next(request)
        resp.set_cookie("site_lang", qlang, max_age=365*86400, path="/")
        return resp
    return await call_next(request)

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_ip(r: Request) -> str:
    xff = r.headers.get("x-forwarded-for")
    if xff: return xff.split(",")[0].strip()
    return r.headers.get("x-real-ip") or r.client.host or ""

def get_auth(r: Request) -> dict:
    try: uid = int(r.cookies.get("OM_UID", "0"))
    except: uid = 0
    if uid <= 0: return {}
    return {"user_id": uid, "username": r.cookies.get("OM_UNAME", ""),
            "avatar": r.cookies.get("OM_AVATAR", "default_avatar.png"),
            "is_premium": int(r.cookies.get("OM_PREMIUM", "0"))}

def lang(r: Request) -> str:
    qlang = r.query_params.get("lang")
    if qlang in ("en", "ru"): return qlang
    l = r.cookies.get("site_lang", "ru")
    if l in ("en","ru"): return l
    return "ru"

def set_auth_cookies(resp, uid, username, avatar="default_avatar.png", premium=0):
    resp.set_cookie("OM_UID", str(uid), max_age=7*86400, path="/")
    resp.set_cookie("OM_UNAME", username, max_age=7*86400, path="/")
    resp.set_cookie("OM_AVATAR", avatar, max_age=7*86400, path="/")
    resp.set_cookie("OM_PREMIUM", str(premium), max_age=7*86400, path="/")

def _norm(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip()

def _hay(a):
    parts = []
    for k in ("name","title","app_name","package","developer","author","category","description"):
        v = a.get(k)
        if isinstance(v, str) and v.strip(): parts.append(v)
    return _norm(" ".join(parts))

def _score(a, terms):
    name = _norm(a.get("name") or a.get("title") or "")
    hay = _hay(a)
    s = 0
    for t in terms:
        if not t: continue
        if t in name: s += 10
        if name.startswith(t): s += 5
        if t in hay: s += 3
    return s

# ─── WEB PAGES ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(r: Request, mode: str = "apps", page: int = 1):
    a = get_auth(r); l = lang(r)
    is_game = mode == "games"
    filtered = [x for x in apps if bool(x.get("is_game")) == is_game]
    top = sorted(filtered, key=lambda x: x.get("downloads", 0), reverse=True)[:10]
    per = 12; total = max(1, (len(filtered)+per-1)//per)
    page = max(1, min(page, total))
    off = (page-1)*per
    paged = filtered[off:off+per]
    return templates.TemplateResponse(r, "index.html", {"request":r,"auth":a,"lang":l,
        "mode":mode,"top":top,"paged":paged,"page":page,"total_pages":total,
        "api_level_to_android":api_level_to_android})

@app.get("/app", response_class=HTMLResponse)
async def app_page(r: Request, id: int = Query(...)):
    a = get_auth(r); d = next((x for x in apps if x["id"] == id), None)
    if not d: return RedirectResponse(url="/")
    return templates.TemplateResponse(r, "app.html", {"request":r,"auth":a,"app":d,
        "api_level_to_android":api_level_to_android,"cat_label":cat_label(cat_code(d))})

@app.get("/categories", response_class=HTMLResponse)
async def categories_page(r: Request):
    a = get_auth(r); l = lang(r)
    game_codes = {"simulators","puzzles","arcade","races","action_games","casual",
        "strategies","table_games","shooter","horror","adventures","rpg",
        "survival","sport","card_games","other_games"}
    ac = []; gc = []
    for c, lbl in CATEGORY_CHOICES.items():
        if c in game_codes: gc.append((c,lbl))
        else: ac.append((c,lbl))
    return templates.TemplateResponse(r, "categories.html", {"request":r,"auth":a,"lang":l,
        "app_categories":ac,"game_categories":gc})

@app.get("/category", response_class=HTMLResponse)
async def category_page(r: Request, code: str = Query("")):
    a = get_auth(r); l = lang(r)
    flt = [x for x in apps if cat_code(x) == code]
    return templates.TemplateResponse(r, "category.html", {"request":r,"auth":a,"lang":l,
        "apps":flt,"category_code":code,"category_label":cat_label(code),
        "api_level_to_android":api_level_to_android})

@app.get("/search", response_class=HTMLResponse)
async def search_page(r: Request, q: str = ""):
    a = get_auth(r); l = lang(r); results = []
    if q:
        qn = _norm(q); terms = [t for t in qn.split() if t]
        scored = []
        for x in apps:
            if all(t in _hay(x) for t in terms):
                scored.append((x, _score(x, terms)))
        scored.sort(key=lambda x: (x[1], x[0].get("id",0)), reverse=True)
        results = [x for x,_ in scored]
    return templates.TemplateResponse(r, "search.html", {"request":r,"auth":a,"lang":l,
        "query":q,"results":results,"api_level_to_android":api_level_to_android})

@app.get("/login", response_class=HTMLResponse)
async def login_page(r: Request, error: str = ""):
    return templates.TemplateResponse(r, "login.html", {"request":r,"auth":get_auth(r),"lang":lang(r),"error":error})

@app.post("/login")
async def login_post(r: Request):
    form = await r.form()
    uname = form.get("username","").strip(); pwd = form.get("password","")
    if not uname or not pwd:
        return templates.TemplateResponse(r, "login.html", {"request":r,"auth":{},"lang":lang(r),"error":"Fill all fields"})
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.username == uname)).scalar_one_or_none()
        if user and check_password_hash(user.password_hash, pwd):
            resp = RedirectResponse(url="/", status_code=302)
            set_auth_cookies(resp, user.id, user.username)
            return resp
        return templates.TemplateResponse(r, "login.html", {"request":r,"auth":{},"lang":lang(r),"error":"Invalid credentials"})
    finally:
        db.close()

@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie("OM_UID", path="/"); resp.delete_cookie("OM_UNAME", path="/")
    resp.delete_cookie("OM_AVATAR", path="/"); resp.delete_cookie("OM_PREMIUM", path="/")
    return resp

@app.get("/register", response_class=HTMLResponse)
async def register_page(r: Request, error: str = ""):
    return templates.TemplateResponse(r, "register.html", {"request":r,"auth":get_auth(r),"lang":lang(r),"error":error})

@app.post("/register")
async def register_post(r: Request):
    form = await r.form()
    uname = form.get("username","").strip(); email = form.get("email","").strip(); pwd = form.get("password","")
    if len(uname) < 3 or len(uname) > 15 or not re.match(r'^[a-zA-Z0-9]+$', uname):
        return templates.TemplateResponse(r, "register.html", {"request":r,"auth":{},"lang":lang(r),"error":"Invalid username"})
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return templates.TemplateResponse(r, "register.html", {"request":r,"auth":{},"lang":lang(r),"error":"Invalid email"})
    if len(pwd) < 4:
        return templates.TemplateResponse(r, "register.html", {"request":r,"auth":{},"lang":lang(r),"error":"Password too short"})
    db = SessionLocal()
    try:
        if db.execute(select(User).where(User.username == uname)).scalar_one_or_none():
            return templates.TemplateResponse(r, "register.html",{"request":r,"auth":{},"lang":lang(r),"error":"Username taken"})
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
            return templates.TemplateResponse(r, "register.html",{"request":r,"auth":{},"lang":lang(r),"error":"Email taken"})
        u = User(username=uname, email=email, password_hash=generate_password_hash(pwd))
        db.add(u); db.commit(); db.refresh(u)
        db.add(UserProfile(user_id=u.id)); db.commit()
        resp = RedirectResponse(url="/", status_code=302)
        set_auth_cookies(resp, u.id, u.username)
        return resp
    finally:
        db.close()

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(r: Request):
    return templates.TemplateResponse(r, "profile.html", {"request":r,"auth":get_auth(r),"lang":lang(r)})

@app.get("/about", response_class=HTMLResponse)
async def about_page(r: Request):
    return templates.TemplateResponse(r, "about.html", {"request":r,"auth":get_auth(r),"lang":lang(r)})

@app.get("/clients", response_class=HTMLResponse)
async def clients_page(r: Request):
    files = []
    clients_dir = os.path.join(BASE_DIR, "html", "clients")
    if os.path.isdir(clients_dir):
        for fn in sorted(os.listdir(clients_dir), key=str.lower):
            if fn.lower().endswith((".apk",".xapk",".apkm")):
                size = os.path.getsize(os.path.join(clients_dir, fn))
                files.append({"name": fn, "size": size})
    return templates.TemplateResponse(r, "clients.html", {
        "request":r,"auth":get_auth(r),"lang":lang(r),"files":files})

# ─── API ─────────────────────────────────────────────────────────────────────

@app.get("/api/apps")
def api_apps(category: str = "", is_game: str = "", limit: int = 0, offset: int = 0):
    flt = apps
    if is_game:
        w = is_game.lower() in ("1","true","yes")
        flt = [a for a in flt if bool(a.get("is_game")) == w]
    if category: flt = [a for a in flt if cat_code(a) == category]
    if limit > 0: flt = flt[offset:offset+limit]
    return flt

@app.get("/api/apps/search")
def api_apps_search(q: str = "", category: str = "", is_game: str = "", limit: int = 0, offset: int = 0):
    flt = apps
    if is_game:
        w = is_game.lower() in ("1","true","yes")
        flt = [a for a in flt if bool(a.get("is_game")) == w]
    if category: flt = [a for a in flt if cat_code(a) == category]
    if q:
        qn = _norm(q); terms = [t for t in qn.split() if t]
        scored = []
        for a in flt:
            if all(t in _hay(a) for t in terms):
                scored.append((a, _score(a, terms)))
        scored.sort(key=lambda x: (x[1], x[0].get("id",0)), reverse=True)
        flt = [a for a,_ in scored]
    if limit > 0: flt = flt[offset:offset+limit]
    return flt

@app.get("/api/app/{app_id}")
def api_app(app_id: int):
    a = next((x for x in apps if x["id"] == app_id), None)
    if not a: raise HTTPException(404)
    return {**a, "category_code": cat_code(a), "category_label": cat_label(cat_code(a))}

@app.get("/api/app/{app_id}/screenshots")
def api_app_screenshots(app_id: int):
    a = next((x for x in apps if x["id"] == app_id), None)
    if not a: raise HTTPException(404)
    return a.get("screenshots", [])

@app.get("/api/app/{app_id}/versions")
def api_app_versions(app_id: int):
    a = next((x for x in apps if x["id"] == app_id), None)
    if not a: raise HTTPException(404)
    return a.get("versions", [])

@app.get("/api/categories")
def api_categories(is_game: str = ""):
    game_codes = {"simulators","puzzles","arcade","races","action_games","casual",
        "strategies","table_games","shooter","horror","adventures","rpg",
        "survival","sport","card_games","other_games"}
    if not is_game:
        return {"apps":[{"code":c,"label":l} for c,l in CATEGORY_CHOICES.items() if c not in game_codes],
                "games":[{"code":c,"label":l} for c,l in CATEGORY_CHOICES.items() if c in game_codes]}
    w = is_game.lower() in ("1","true","yes")
    cats = game_codes if w else set(CATEGORY_CHOICES.keys())-game_codes
    return [{"code":c,"label":CATEGORY_CHOICES[c],"is_game":w} for c in cats]

@app.get("/api/top-apps")
def api_top_apps():
    return sorted([a for a in apps if not a.get("is_game")], key=lambda x: x.get("downloads",0), reverse=True)[:10]

@app.get("/api/top-games")
def api_top_games():
    return sorted([a for a in apps if a.get("is_game")], key=lambda x: x.get("downloads",0), reverse=True)[:10]

@app.get("/api/banners")
def api_banners():
    link_map = BANNER_LINKS
    items = []
    if os.path.isdir(BANNERS_DIR):
        for fn in sorted(os.listdir(BANNERS_DIR)):
            if fn.lower().endswith((".jpg",".jpeg",".png",".webp")):
                items.append({"image":fn,"url":link_map.get(fn,"")})
    return items

@app.get("/api/app/{app_id}/reviews")
def get_reviews(app_id: int, viewer_id: int = 0):
    db = SessionLocal()
    try:
        reviews = db.execute(select(Review).where(Review.app_id == app_id).order_by(Review.created_at.desc())).scalars().all()
        result = []
        for r in reviews:
            u = db.get(User, r.user_id)
            p = db.execute(select(UserProfile).where(UserProfile.user_id == r.user_id)).scalar_one_or_none()
            likes = db.execute(select(func.count(ReviewReaction.id)).where(
                ReviewReaction.review_id == r.id, ReviewReaction.value == 1)).scalar() or 0
            dislikes = db.execute(select(func.count(ReviewReaction.id)).where(
                ReviewReaction.review_id == r.id, ReviewReaction.value == -1)).scalar() or 0
            cc = db.execute(select(func.count(ReviewComment.id)).where(ReviewComment.review_id == r.id)).scalar() or 0
            ur = 0
            if viewer_id:
                rr = db.execute(select(ReviewReaction.value).where(
                    ReviewReaction.review_id == r.id, ReviewReaction.user_id == viewer_id)).scalar_one_or_none()
                if rr: ur = rr
            result.append({
                "id":r.id,"user_id":r.user_id,"username":u.username if u else "Unknown",
                "avatar":p.avatar if p else "default_avatar.png",
                "rating":r.rating,"comment":r.comment or "",
                "created_at":r.created_at.isoformat() if r.created_at else "",
                "likes":likes,"dislikes":dislikes,"user_reaction":ur,"comments_count":cc,
            })
        return result
    finally:
        db.close()

class ReviewIn(BaseModel):
    user_id: int; rating: int; comment: str = ""; ip: str = ""

@app.post("/api/app/{app_id}/review")
def create_review(app_id: int, data: ReviewIn):
    if data.rating < 1 or data.rating > 5: raise HTTPException(400, "Rating 1-5")
    db = SessionLocal()
    try:
        if db.execute(select(Review).where(Review.app_id == app_id, Review.user_id == data.user_id)).first():
            raise HTTPException(400, "Already reviewed")
        db.add(Review(app_id=app_id, user_id=data.user_id, rating=data.rating, comment=data.comment))
        db.commit()
        return {"success":True}
    finally:
        db.close()

@app.get("/api/review/{review_id}/comments")
def get_comments(review_id: int):
    db = SessionLocal()
    try:
        rows = db.execute(
            select(ReviewComment, User, UserProfile)
            .join(User, ReviewComment.user_id == User.id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(ReviewComment.review_id == review_id).order_by(ReviewComment.created_at)
        ).all()
        return [{"id":c.id,"user_id":u.id,"username":u.username,
            "avatar":p.avatar if p else "default_avatar.png",
            "text":c.text,"created_at":c.created_at.isoformat() if c.created_at else ""}
            for c,u,p in rows]
    finally:
        db.close()

class CommentIn(BaseModel):
    user_id: int; text: str

@app.post("/api/review/{review_id}/comment")
def add_comment(review_id: int, data: CommentIn):
    if not data.text or len(data.text) > 300: raise HTTPException(400)
    db = SessionLocal()
    try:
        db.add(ReviewComment(review_id=review_id, user_id=data.user_id, text=data.text))
        db.commit()
        return {"success":True}
    finally:
        db.close()

class ReactIn(BaseModel):
    user_id: int; value: int

@app.post("/api/review/{review_id}/reaction")
def set_reaction(review_id: int, data: ReactIn):
    if data.value not in (-1,0,1): raise HTTPException(400)
    db = SessionLocal()
    try:
        if data.value == 0:
            db.execute(delete(ReviewReaction).where(
                ReviewReaction.review_id == review_id, ReviewReaction.user_id == data.user_id))
        else:
            er = db.execute(select(ReviewReaction).where(
                ReviewReaction.review_id == review_id, ReviewReaction.user_id == data.user_id)).scalar_one_or_none()
            if er: er.value = data.value
            else: db.add(ReviewReaction(review_id=review_id, user_id=data.user_id, value=data.value))
        db.commit()
        likes = db.execute(select(func.count(ReviewReaction.id)).where(
            ReviewReaction.review_id == review_id, ReviewReaction.value == 1)).scalar() or 0
        dislikes = db.execute(select(func.count(ReviewReaction.id)).where(
            ReviewReaction.review_id == review_id, ReviewReaction.value == -1)).scalar() or 0
        return {"likes":likes,"dislikes":dislikes,"user_reaction":data.value}
    finally:
        db.close()

@app.post("/api/review/{review_id}/report")
def report_review(review_id: int, data: dict):
    db = SessionLocal()
    try:
        db.add(Report(review_id=review_id, reporter_user_id=data.get("user_id",0), reason=data.get("reason",""), status="new"))
        db.commit()
        return {"success":True}
    finally:
        db.close()

@app.get("/api/user/{user_id}/profile")
def get_profile(user_id: int):
    db = SessionLocal()
    try:
        p = db.execute(select(UserProfile).where(UserProfile.user_id == user_id)).scalar_one_or_none()
        if not p: return {"error":"Not found"}
        return {"avatar":p.avatar,"description":p.description or "","is_premium":p.is_premium}
    finally:
        db.close()

@app.get("/api/download/{app_id}")
def download_app(app_id: int, r: Request, user_id: int = 0):
    a = next((x for x in apps if x["id"] == app_id), None)
    if not a: raise HTTPException(404)
    ip = get_ip(r); db = SessionLocal()
    try:
        try:
            db.add(DownloadIP(app_id=app_id, ip=ip))
            db.add(Download(app_id=app_id, user_id=user_id if user_id else None))
            db.commit()
        except IntegrityError: db.rollback()
    finally: db.close()
    if CDN["base_url"]:
        return RedirectResponse(url=cdn_url(f"/html/apps/{a['apk_file']}"))
    fp = os.path.join(UPLOAD_DIR, a.get("apk_file",""))
    if not os.path.isfile(fp): raise HTTPException(404)
    return FileResponse(fp, media_type="application/vnd.android.package-archive", filename=a["apk_file"])

@app.get("/api/download/{app_id}/{version}")
def download_app_version(app_id: int, version: str, r: Request, user_id: int = 0):
    a = next((x for x in apps if x["id"] == app_id), None)
    if not a: raise HTTPException(404)
    v = next((x for x in a.get("versions",[]) if x["version"] == version), None)
    if not v: raise HTTPException(404)
    ip = get_ip(r); db = SessionLocal()
    try:
        try:
            db.add(DownloadIP(app_id=app_id, ip=ip))
            db.add(Download(app_id=app_id, user_id=user_id if user_id else None))
            db.commit()
        except IntegrityError: db.rollback()
    finally: db.close()
    if CDN["base_url"]:
        return RedirectResponse(url=cdn_url(f"/html/apps/{v['apk_file']}"))
    fp = os.path.join(UPLOAD_DIR, v.get("apk_file",""))
    if not os.path.isfile(fp): raise HTTPException(404)
    return FileResponse(fp, media_type="application/vnd.android.package-archive", filename=v["apk_file"])

@app.get("/api/stats")
def api_stats():
    db = SessionLocal()
    try:
        return {"total_downloads": db.execute(select(func.count(Download.id))).scalar() or 0,
                "total_users": db.execute(select(func.count(User.id))).scalar() or 0,
                "total_reviews": db.execute(select(func.count(Review.id))).scalar() or 0}
    finally: db.close()

@app.get("/api/client-update")
def api_client_update():
    path = os.path.join(BASE_DIR, "client_update.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version_code": 0}

@app.get("/api/avatars")
def api_avatars():
    return ["avatar1.png","avatar2.png","avatar3.png","avatar4.png","avatar4.gif","avatar5.gif",
            "avatar6.gif","avatar7.gif","avatar8.gif","avatar9.gif","avatar10.gif","avatar11.gif",
            "avatar12.gif","avatar13.gif","avatar14.gif","avatar15.gif","avatar16.gif","avatar17.gif"]

# ─── ADMIN PANEL ────────────────────────────────────────────────────────────

@app.get("/admin/", response_class=HTMLResponse)
def admin_login_page(r: Request):
    token = r.cookies.get("admin_token")
    expected = hmac.new(ADMIN_CFG["secret_key"].encode(), b"admin_session", "sha256").hexdigest()
    if token == expected:
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return templates.TemplateResponse(r, "admin/login.html", {"request": r})

@app.post("/admin/")
def admin_login(r: Request, password: str = Form(...)):
    if password != ADMIN_CFG["password"]:
        return templates.TemplateResponse(r, "admin/login.html", {
            "request": r, "error": "Неверный пароль"})
    token = hmac.new(ADMIN_CFG["secret_key"].encode(), b"admin_session", "sha256").hexdigest()
    resp = RedirectResponse(url="/admin/dashboard", status_code=302)
    resp.set_cookie("admin_token", token, max_age=86400, httponly=True, samesite="lax")
    return resp

@app.get("/admin/logout")
def admin_logout():
    resp = RedirectResponse(url="/admin/", status_code=302)
    resp.delete_cookie("admin_token")
    return resp

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(r: Request):
    redir = admin_login_required(r)
    if redir: return redir
    cat_counts = {}
    for a in apps:
        c = cat_code(a)
        cat_counts[c] = cat_counts.get(c, 0) + 1
    return templates.TemplateResponse(r, "admin/dashboard.html", {
        "request": r, "apps": apps, "cat_counts": cat_counts,
        "total": len(apps), "cat_label": cat_label})

@app.get("/admin/app/new", response_class=HTMLResponse)
def admin_new_app_page(r: Request):
    redir = admin_login_required(r)
    if redir: return redir
    return templates.TemplateResponse(r, "admin/edit.html", {
        "request": r, "app": None, "categories": CATEGORY_CHOICES,
        "api_levels": sorted(API_MAP.keys())})

@app.post("/admin/app/new")
async def admin_new_app(r: Request):
    redir = admin_login_required(r)
    if redir: return redir
    data = await r.form()
    new_app = _build_app_from_form(data)
    new_app["id"] = max((a["id"] for a in apps), default=0) + 1
    apps.append(new_app)
    write_apps_data(apps)
    return RedirectResponse(url=f"/admin/app/{new_app['id']}/edit", status_code=302)

@app.get("/admin/app/{app_id}/edit", response_class=HTMLResponse)
def admin_edit_app_page(r: Request, app_id: int):
    redir = admin_login_required(r)
    if redir: return redir
    a = next((x for x in apps if x["id"] == app_id), None)
    if not a: return HTMLResponse("App not found", status_code=404)
    return templates.TemplateResponse(r, "admin/edit.html", {
        "request": r, "app": a, "categories": CATEGORY_CHOICES,
        "api_levels": sorted(API_MAP.keys())})

@app.post("/admin/app/{app_id}/edit")
async def admin_edit_app(r: Request, app_id: int):
    redir = admin_login_required(r)
    if redir: return redir
    a = next((x for x in apps if x["id"] == app_id), None)
    if not a: raise HTTPException(404)
    data = await r.form()
    updated = _build_app_from_form(data, existing=a)
    idx = next(i for i, x in enumerate(apps) if x["id"] == app_id)
    apps[idx] = updated
    write_apps_data(apps)
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/app/{app_id}/delete")
def admin_delete_app(r: Request, app_id: int):
    redir = admin_login_required(r)
    if redir: return redir
    global apps
    apps = [a for a in apps if a["id"] != app_id]
    write_apps_data(apps)
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/upload/apk")
def admin_upload_apk(r: Request, file: UploadFile = File(...)):
    redir = admin_login_required(r)
    if redir: return JSONResponse({"error": "auth"}, status_code=401)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_APK_EXT:
        return JSONResponse({"error": f"Недопустимый формат: {ext}"}, status_code=400)
    name = f"{uuid4().hex}{ext}"
    save_upload(os.path.join(UPLOAD_DIR, name), file)
    return JSONResponse({"filename": name})

@app.post("/admin/upload/icon")
def admin_upload_icon(r: Request, file: UploadFile = File(...)):
    redir = admin_login_required(r)
    if redir: return JSONResponse({"error": "auth"}, status_code=401)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_ICON_EXT:
        return JSONResponse({"error": f"Недопустимый формат: {ext}"}, status_code=400)
    name = f"{uuid4().hex}{ext}"
    save_upload(os.path.join(UPLOAD_DIR, name), file)
    return JSONResponse({"filename": name})

@app.post("/admin/upload/screenshot")
def admin_upload_screenshot(r: Request, file: UploadFile = File(...)):
    redir = admin_login_required(r)
    if redir: return JSONResponse({"error": "auth"}, status_code=401)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_SCREENSHOT_EXT:
        return JSONResponse({"error": f"Недопустимый формат: {ext}"}, status_code=400)
    name = f"{uuid4().hex}{ext}"
    save_upload(os.path.join(SCREENSHOTS_DIR, name), file)
    return JSONResponse({"filename": name})

# ─── ADMIN HELPERS ──────────────────────────────────────────────────────────

def _build_app_from_form(data, existing=None):
    """Собирает dict приложения из POST-данных формы админки."""
    a = dict(existing or {})
    a["name"] = data.get("name", a.get("name", ""))
    a["author"] = data.get("author", a.get("author", ""))
    a["package"] = data.get("package", a.get("package", ""))
    a["category_code"] = data.get("category_code", a.get("category_code", ""))
    a["category"] = cat_label(a["category_code"])
    a["version"] = data.get("version", a.get("version", "1.0"))
    a["version_code"] = data.get("version_code", a.get("version_code", "1"))
    a["min_sdk"] = int(data.get("min_sdk", a.get("min_sdk", 0)))
    a["target_sdk"] = int(data.get("target_sdk", a.get("target_sdk", 0)))
    a["description"] = data.get("description", a.get("description", ""))
    a["whatsnew"] = data.get("whatsnew", a.get("whatsnew", ""))
    a["size"] = data.get("size", a.get("size", ""))
    a["downloads"] = int(data.get("downloads", a.get("downloads", 0)))
    a["rating"] = float(data.get("rating", a.get("rating", 0)))
    a["rated_times"] = int(data.get("rated_times", a.get("rated_times", 0)))
    a["is_game"] = bool(data.get("is_game", a.get("is_game", False)))
    a["has_premium"] = bool(data.get("has_premium", a.get("has_premium", False)))
    a["language"] = data.get("language", a.get("language", "RU"))
    a["license_type"] = data.get("license_type", a.get("license_type", "Free"))
    a["apk_file"] = data.get("apk_file", a.get("apk_file", ""))
    a["banner_file"] = data.get("banner_file", a.get("banner_file", ""))
    a["icon"] = data.get("icon", a.get("icon", ""))
    a["screenshots"] = a.get("screenshots", [])
    if data.get("new_screenshot"):
        ss = a["screenshots"][:]
        ss.append(data["new_screenshot"])
        a["screenshots"] = ss
    return a

# ─── RUN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)