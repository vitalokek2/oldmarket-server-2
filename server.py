import os
import re
import json
import requests
import threading
import time
from functools import wraps
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, request, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, text, case
from sqlalchemy.exc import IntegrityError, DatabaseError
from apps_data import apps
import random
import string
import sqlite3

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oldmarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'html/apps'
app.config['SECRET_KEY'] = ''
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {"timeout": 30},
    "pool_pre_ping": True,
}
BANNERS_DIR = os.environ.get("BANNERS_DIR", os.path.join("html", "banners"))
os.makedirs(BANNERS_DIR, exist_ok=True)
db = SQLAlchemy(app)
#Admin settings
ADMIN_PASSWORD = os.environ.get("passwd", "passwd")
ADMIN_ALLOWED_IPS = set((os.environ.get("OLDMARKET_ADMIN_ALLOWED_IPS", "144.31.197.62,144.31.16.165").split(",")))
#Telegram settings
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "token").strip()
TG_ADMIN_ID = int(os.environ.get("TG_ADMIN_ID", "0000000000") or "0")
TG_WEBHOOK_SECRET = os.environ.get("TG_WEBHOOK_SECRET", "").strip()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_ip = db.Column(db.String(50), nullable=True)
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class ReviewReaction(db.Model):
    __tablename__ = 'review_reaction'
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    value = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (
        db.UniqueConstraint('review_id', 'user_id', name='uq_review_reaction_review_user'),
    )
class ReactionRateLimit(db.Model):
    __tablename__ = 'reaction_rate_limit'
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, nullable=False, index=True)
    ip = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class ReviewComment(db.Model):
    __tablename__ = 'review_comment'
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    text = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class Download(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class DownloadIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, nullable=False, index=True)
    ip = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('app_id', 'ip', name='uq_download_ip'),
    )
class ClientAnalytics(db.Model):
    __tablename__ = 'client_analytics'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=True, index=True)
    api_level = db.Column(db.Integer, nullable=False, index=True)
    android_version = db.Column(db.String(50), nullable=False, index=True)
    app_version_code = db.Column(db.Integer, nullable=False, index=True)
    app_version_name = db.Column(db.String(50), nullable=True)
    device_model = db.Column(db.String(120), nullable=True)
    manufacturer = db.Column(db.String(120), nullable=True)
    lang = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    hits = db.Column(db.Integer, default=1)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    avatar = db.Column(db.String(100), default='avatar1.png')
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_premium = db.Column(db.Integer, default=0)
    premium_until = db.Column(db.DateTime, nullable=True)
class RegistrationIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False, index=True)
    day = db.Column(db.Date, nullable=False, index=True)
    count = db.Column(db.Integer, default=0)
    __table_args__ = (
        db.UniqueConstraint('ip', 'day', name='uq_reg_ip_day'),
    )
class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False, index=True)
    username = db.Column(db.String(80), nullable=True, index=True)
    success = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class BlockedIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False, unique=True)
    reason = db.Column(db.String(200), nullable=False)
    until = db.Column(db.DateTime, nullable=False)
class SecurityEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=True, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class CommentRateLimit(db.Model):
    __tablename__ = 'comment_rate_limit'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    review_id = db.Column(db.Integer, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class ReactionIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, nullable=False, index=True)
    ip = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('review_id', 'ip', name='uq_reaction_ip_review'),
    )

class TgModerator(db.Model):
    __tablename__ = 'tg_moderator'
    id = db.Column(db.Integer, primary_key=True)
    tg_user_id = db.Column(db.Integer, nullable=False, index=True)
    app_id = db.Column(db.Integer, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('tg_user_id', 'app_id', name='uq_tg_moderator_user_app'),
    )
class Report(db.Model):
    __tablename__ = 'report'
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, nullable=False, index=True)
    reporter_user_id = db.Column(db.Integer, nullable=False, index=True)
    reason = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='new', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    handled_by_tg = db.Column(db.Integer, nullable=True)
    handled_action = db.Column(db.String(20), nullable=True)
class Submission(db.Model):
    __tablename__ = "submission"
    id = db.Column(db.Integer, primary_key=True)
    tg_user_id = db.Column(db.Integer, index=True)
    username = db.Column(db.String(100))
    app_name = db.Column(db.String(200))
    author = db.Column(db.String(200))
    description = db.Column(db.Text)
    icon_path = db.Column(db.String(200))
    version = db.Column(db.String(50))
    app_type = db.Column(db.String(50))
    category_code = db.Column(db.String(50))
    category_label = db.Column(db.String(100))
    min_android = db.Column(db.String(50))
    apk_url = db.Column(db.String(500))
    screenshots = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending", index=True)
    reject_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class TgPremium(db.Model):
    __tablename__ = "tg_premium"
    tg_user_id = db.Column(db.Integer, primary_key=True)
    expire_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PendingTelegramRegistration(db.Model):
    __tablename__ = "pending_tg_registration"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)

    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    tg_user_id = db.Column(db.Integer, nullable=True, index=True)
    tg_username = db.Column(db.String(120), nullable=True)

    is_linked = db.Column(db.Boolean, default=False, index=True)
    is_finished = db.Column(db.Boolean, default=False, index=True)

    created_ip = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)


class TelegramAccountLock(db.Model):
    __tablename__ = "telegram_account_lock"

    id = db.Column(db.Integer, primary_key=True)
    tg_user_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    tg_username = db.Column(db.String(120), nullable=True)

    first_user_id = db.Column(db.Integer, nullable=True, index=True)
    first_username = db.Column(db.String(80), nullable=True)
    is_consumed = db.Column(db.Boolean, default=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserTelegramLink(db.Model):
    __tablename__ = "user_telegram_link"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    tg_user_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    tg_username = db.Column(db.String(120), nullable=True)
    linked_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)



class PendingUserTelegramLink(db.Model):
    __tablename__ = "pending_user_telegram_link"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    tg_user_id = db.Column(db.Integer, nullable=True, index=True)
    tg_username = db.Column(db.String(120), nullable=True)

    is_finished = db.Column(db.Boolean, default=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)


class TgPasswordReset(db.Model):
    __tablename__ = "tg_password_reset"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    tg_user_id = db.Column(db.Integer, nullable=False, index=True)
    temp_password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

submission_states = {}
submission_cache = {}
reject_reason_waiting = {}
account_password_reset_waiting = {}
AVAILABLE_AVATARS = [
    'avatar1.png', 'avatar2.png', 'avatar3.png', 'avatar4.png', 'avatar4.gif', 'avatar5.gif',
    'avatar6.gif', 'avatar7.gif', 'avatar11.gif', 'avatar12.gif', 'avatar13.gif', 'avatar14.gif',
    'avatar8.gif', 'avatar9.gif', 'avatar10.gif', 'avatar15.gif', 'avatar16.gif', 'avatar17.gif',
]
BAD_WORDS = [

]
DONATE_URL_1 = "https://dalink.to/oldmarket"
DONATE_URL_2 = "https://yoomoney.ru/to/4100117591116914"
STATE_APP_NAME = "waiting_app_name"
STATE_AUTHOR = "waiting_author"
STATE_DESCRIPTION = "waiting_description"
STATE_ICON = "waiting_icon"
STATE_VERSION = "waiting_version"
STATE_APP_TYPE = "waiting_app_type"
STATE_CATEGORY = "waiting_category"
STATE_MIN_ANDROID = "waiting_min_android"
STATE_SCREENSHOTS = "waiting_screenshots"
STATE_APK_URL = "waiting_apk_url"
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
    ("notworked", "Не рабочие(для красоты)"),
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
APP_CATEGORY_CHOICES = [
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
    ("notworked", "Не рабочие(для красоты)"),
    ("others", "Другие"),
]
GAME_CATEGORY_CHOICES = [
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
API_CHOICES = [
    ("1", "API 1 - Android 1.0"),
    ("2", "API 2 - Android 1.1"),
    ("3", "API 3 - Android 1.5"),
    ("4", "API 4 - Android 1.6"),
    ("5", "API 5 - Android 2.0"),
    ("6", "API 6 - Android 2.0.1"),
    ("7", "API 7 - Android 2.1"),
    ("8", "API 8 - Android 2.2"),
    ("9", "API 9 - Android 2.3.0"),
    ("10", "API 10 - Android 2.3.3"),
    ("11", "API 11 - Android 3.0"),
    ("12", "API 12 - Android 3.1"),
    ("13", "API 13 - Android 3.2"),
    ("14", "API 14 - Android 4.0.1"),
    ("15", "API 15 - Android 4.0.3"),
    ("16", "API 16 - Android 4.1"),
    ("17", "API 17 - Android 4.2"),
    ("18", "API 18 - Android 4.3"),
    ("19", "API 19 - Android 4.4"),
    ("20", "API 20 - Android 4.4W"),
]

def api_level_to_android(api_level: int) -> str:
    mapping = {
        1: "Android 1.0", 2: "Android 1.1", 3: "Android 1.5", 4: "Android 1.6",
        5: "Android 2.0", 6: "Android 2.0.1", 7: "Android 2.1", 8: "Android 2.2",
        9: "Android 2.3", 10: "Android 2.3.3", 11: "Android 3.0", 12: "Android 3.1",
        13: "Android 3.2", 14: "Android 4.0.1", 15: "Android 4.0.3", 16: "Android 4.1",
        17: "Android 4.2", 18: "Android 4.3", 19: "Android 4.4", 20: "Android 4.4W",
        21: "Android 5.0", 22: "Android 5.1", 23: "Android 6.0", 24: "Android 7.0",
        25: "Android 7.1", 26: "Android 8.0", 27: "Android 8.1", 28: "Android 9",
        29: "Android 10", 30: "Android 11", 31: "Android 12", 32: "Android 12L",
        33: "Android 13", 34: "Android 14", 35: "Android 15"
    }
    return mapping.get(int(api_level or 0), f"Android API {api_level}")

def get_real_ip():
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        return xff.split(',')[0].strip()
    return request.headers.get('CF-Connecting-IP') or \
           request.headers.get('X-Real-IP') or \
           request.remote_addr
def contains_bad_words(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    for w in BAD_WORDS:
        if w in t:
            return True
    return False
def is_ip_blocked(ip: str) -> bool:
    if not ip:
        return False
    block = BlockedIP.query.filter_by(ip=ip).first()
    if not block:
        return False
    if block.until <= datetime.utcnow():
        db.session.delete(block)
        db.session.commit()
        return False
    return True
def get_client_update():
    try:
        with open("client_update.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("CLIENT UPDATE ERROR:", e)
        return {
            "version_code": 0,
            "version_name": "0",
            "url": "",
            "notes_ru": "",
            "notes_en": ""
        }
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ip = get_real_ip()
        if ip not in ADMIN_ALLOWED_IPS:
            return jsonify({"error": "Admin access denied (ip)"}), 403
        pwd = request.headers.get("X-Admin-Password", "")
        if not pwd or pwd != ADMIN_PASSWORD:
            return jsonify({"error": "Admin auth failed"}), 401
        return fn(*args, **kwargs)
    return wrapper
def log_security(event_type: str, ip: str = None, user_id: int = None, details: str = None):
    ev = SecurityEvent(ip=ip, user_id=user_id, event_type=event_type, details=details)
    db.session.add(ev)
    db.session.commit()
    print(f"[SECURITY] {datetime.utcnow().isoformat()} [{event_type}] ip={ip} user_id={user_id} {details or ''}")
def ban_ip(ip: str, reason: str, hours: int = 1):
    if not ip:
        return
    until = datetime.utcnow() + timedelta(hours=hours)
    blk = BlockedIP.query.filter_by(ip=ip).first()
    if not blk:
        blk = BlockedIP(ip=ip, reason=reason, until=until)
        db.session.add(blk)
    else:
        blk.until = until
        blk.reason = reason
    db.session.commit()
    log_security("ip_banned", ip=ip, details=f"{reason}, until={until.isoformat()}")
def check_registration_rate_limit(ip: str, limit_per_day: int = 3) -> bool:
    today = date.today()
    rec = RegistrationIP.query.filter_by(ip=ip, day=today).first()
    if rec and rec.count >= limit_per_day:
        return False
    return True
def increment_registration_ip(ip: str):
    today = date.today()
    rec = RegistrationIP.query.filter_by(ip=ip, day=today).first()
    if not rec:
        rec = RegistrationIP(ip=ip, day=today, count=1)
        db.session.add(rec)
    else:
        rec.count += 1
    db.session.commit()
def record_download_once(app_id: int, user_id=None, user_ip: str = None) -> bool:
    """
    Возвращает True, если это первое скачивание с этого IP для app_id
    и счётчик был увеличен.
    Возвращает False, если такой IP уже был.
    Бросает DatabaseError при проблемах с БД.
    """
    if not user_ip:
        return False

    try:
        db.session.add(DownloadIP(app_id=app_id, ip=user_ip))
        db.session.flush()

        db.session.add(Download(app_id=app_id, user_id=user_id))
        db.session.commit()
        return True

    except IntegrityError:
        db.session.rollback()
        log_security("download_duplicate_ip", ip=user_ip, details=f"app_id={app_id}")
        return False

    except DatabaseError:
        db.session.rollback()
        raise

    except Exception:
        db.session.rollback()
        raise
def record_login_attempt(ip: str, username: str, success: bool):
    att = LoginAttempt(ip=ip, username=username, success=success)
    db.session.add(att)
    db.session.commit()
def check_login_bruteforce(ip: str, window_minutes: int = 15, max_failures: int = 5) -> bool:
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    fails = LoginAttempt.query.filter(
        LoginAttempt.ip == ip,
        LoginAttempt.created_at >= cutoff,
        LoginAttempt.success == False
    ).count()
    return fails >= max_failures
def build_apps_with_stats(apps_list):
    app_ids = [a["id"] for a in apps_list]
    if not app_ids:
        return []
    reviews_rows = db.session.query(
        Review.app_id.label("app_id"),
        func.avg(Review.rating).label("avg_rating"),
        func.count(Review.id).label("review_count"),
    ).filter(
        Review.app_id.in_(app_ids)
    ).group_by(
        Review.app_id
    ).all()
    reviews_map = {
        r.app_id: (float(r.avg_rating) if r.avg_rating is not None else 0.0, int(r.review_count))
        for r in reviews_rows
    }
    downloads_rows = db.session.query(
        Download.app_id.label("app_id"),
        func.count(Download.id).label("downloads"),
    ).filter(
        Download.app_id.in_(app_ids)
    ).group_by(
        Download.app_id
    ).all()
    downloads_map = {d.app_id: int(d.downloads) for d in downloads_rows}
    out = []
    for a in apps_list:
        avg_rating, review_count = reviews_map.get(a["id"], (0.0, 0))
        downloads = downloads_map.get(a["id"], 0)
        category_code = _category_code_for_app(a)
        category_label = _category_label_for_app(a)
        out.append({
            **a,
            "category_code": category_code,
            "category_label": category_label,
            "rating": round(avg_rating, 1),
            "downloads": downloads,
            "review_count": review_count
        })
    return out
def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s
def _app_search_haystack(a: dict) -> str:
    parts = []
    for k in ("name", "title", "app_name", "package", "developer", "author", "category", "description", "desc"):
        v = a.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    for k in ("tags", "genres"):
        v = a.get(k)
        if isinstance(v, list):
            parts.extend([str(x) for x in v if x is not None])
    return _norm(" ".join(parts))
def _search_score(a: dict, q_terms: list[str]) -> int:
    name = _norm(a.get("name") or a.get("title") or a.get("app_name") or "")
    hay = _app_search_haystack(a)
    score = 0
    for t in q_terms:
        if not t:
            continue
        if t in name:
            score += 10
            if name.startswith(t):
                score += 5
        if t in hay:
            score += 3
    return score


def _category_code_for_app(a: dict):
    for key in ("category_code", "category", "genre_code", "genre"):
        val = a.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""

def _category_label_maps():
    app_map = dict(APP_CATEGORY_CHOICES)
    game_map = dict(GAME_CATEGORY_CHOICES)
    all_map = dict(CATEGORY_CHOICES)
    return app_map, game_map, all_map

def _category_label_for_app(a: dict):
    code = _category_code_for_app(a)
    app_map, game_map, all_map = _category_label_maps()
    if code in all_map:
        return all_map[code]
    for key in ("category_label", "genre_label"):
        val = a.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    val = a.get("category")
    if isinstance(val, str) and val.strip() and val != code:
        return val.strip()
    return code

def generate_link_code():
    return str(random.randint(100000, 999999))

def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))

def cleanup_pending_tg_regs():
    now = datetime.utcnow()
    PendingTelegramRegistration.query.filter(
        PendingTelegramRegistration.expires_at < now,
        PendingTelegramRegistration.is_finished == False
    ).delete(synchronize_session=False)
    db.session.commit()

def cleanup_pending_user_tg_links():
    now = datetime.utcnow()
    PendingUserTelegramLink.query.filter(
        PendingUserTelegramLink.expires_at < now,
        PendingUserTelegramLink.is_finished == False
    ).delete(synchronize_session=False)
    db.session.commit()

def tg_api(method: str, payload: dict):
    if not TG_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print("TG API error:", e)
        return None
def tg_send_message(chat_id: int, text: str, reply_markup: dict = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_api("sendMessage", payload)
    print("TG SEND MESSAGE RESULT:", res)
    return res
def tg_edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict = None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return tg_api("editMessageText", payload)
def tg_answer_callback(callback_query_id: str, text: str = ""):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = False
    return tg_api("answerCallbackQuery", payload)
def tg_main_keyboard(user_id):
    buttons = [
        [{"text": "📱 Предложить приложение", "callback_data": "submit_app"}],
        [{"text": "💸 Поддержать проект", "url": "https://dalink.to/oldmarket"}],
    ]
    if user_id == TG_ADMIN_ID:
        buttons.append([{"text": "📊 Статистика", "callback_data": "stats"}])
    return {"inline_keyboard": buttons}
def _trim200(s: str) -> str:
    s = (s or "").strip()
    if len(s) <= 200:
        return s
    return s[:200] + "…"
def is_tg_premium(user_id: int) -> bool:
    rec = TgPremium.query.filter_by(tg_user_id=int(user_id)).first()
    return bool(rec and rec.expire_at > datetime.utcnow())
def set_tg_premium(user_id: int, days: int):
    expire = datetime.utcnow() + timedelta(days=days)
    rec = TgPremium.query.filter_by(tg_user_id=int(user_id)).first()
    if not rec:
        rec = TgPremium(tg_user_id=int(user_id), expire_at=expire)
        db.session.add(rec)
    else:
        rec.expire_at = expire
    db.session.commit()
    return expire
def clear_tg_premium(user_id: int):
    TgPremium.query.filter_by(tg_user_id=int(user_id)).delete()
    db.session.commit()
def tg_get_file(file_id: str):
    res = tg_api("getFile", {"file_id": file_id})
    if not res or not res.get("ok"):
        return None
    return (res.get("result") or {}).get("file_path")
def tg_download_file(file_path: str, dst_path: str) -> bool:
    if not TG_BOT_TOKEN or not file_path:
        return False
    url = f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_path}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return False
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        with open(dst_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print("TG download error:", e)
        return False
def tg_send_photo(chat_id: int, photo_path: str, caption: str = None, reply_markup: dict = None):
    if not TG_BOT_TOKEN or not os.path.exists(photo_path):
        return None
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    data = {"chat_id": str(chat_id), "parse_mode": "HTML"}
    if caption:
        data["caption"] = caption
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            r = requests.post(url, data=data, files=files, timeout=30)
        return r.json()
    except Exception as e:
        print("TG sendPhoto error:", e)
        return None
def tg_send_media_group(chat_id: int, media_paths: list[str]):
    valid = [p for p in media_paths[:10] if p and os.path.exists(p)]
    if not valid or not TG_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMediaGroup"
    media = []
    files = {}
    try:
        for i, path in enumerate(valid):
            key = f"file{i}"
            files[key] = open(path, "rb")
            media.append({"type": "photo", "media": f"attach://{key}"})
        data = {"chat_id": str(chat_id), "media": json.dumps(media, ensure_ascii=False)}
        r = requests.post(url, data=data, files=files, timeout=60)
        return r.json()
    except Exception as e:
        print("TG sendMediaGroup error:", e)
        return None
    finally:
        for f in files.values():
            try:
                f.close()
            except Exception:
                pass
def tg_main_keyboard(user_id: int):
    buttons = [
        [{"text": "📱 Предложить приложение", "callback_data": "submit_app"}],
        [{"text": "👤 Аккаунт в OldMarket", "callback_data": "om_account"}],
        [{"text": "⭐ Премиум подписка", "callback_data": "paid_add"}],
        [{"text": "🛒 Реклама на баннер", "callback_data": "ad_banner"}],
        [{"text": "💸 Поддержать проект", "callback_data": "donate"}],
    ]
    if int(user_id) == int(TG_ADMIN_ID):
        buttons.append([{"text": "📊 Статистика", "callback_data": "stats"}])
    return {"inline_keyboard": buttons}
def tg_with_cancel(rows=None):
    rows = list(rows or [])
    rows.append([{"text": "❌ Отмена", "callback_data": "cancel_submission"}])
    return {"inline_keyboard": rows}
def tg_category_keyboard():
    rows, row = [], []
    for code, label in CATEGORY_CHOICES:
        row.append({"text": label, "callback_data": f"cat_{code}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "⬅️ Назад", "callback_data": "back_to_main"}])
    return tg_with_cancel(rows)
def tg_app_type_keyboard():
    return tg_with_cancel([
        [{"text": "🎮 Игра", "callback_data": "type_game"}],
        [{"text": "📱 Приложение", "callback_data": "type_app"}],
    ])
def tg_api_keyboard():
    rows = [[{"text": label, "callback_data": f"minapi_{code}"}] for code, label in API_CHOICES]
    rows.append([{"text": "⬅️ Назад", "callback_data": "back_to_main"}])
    return tg_with_cancel(rows)
def tg_screens_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "⏭ Пропустить", "callback_data": "skip_screens"},
                {"text": "✅ Готово", "callback_data": "done_screens"},
            ],
            [{"text": "❌ Отмена", "callback_data": "cancel_submission"}],
        ]
    }
def tg_submission_admin_keyboard(submission_id: int):
    return {
        "inline_keyboard": [[
            {"text": "✅ Принять", "callback_data": f"admin_approve_{submission_id}"},
            {"text": "❌ Отклонить", "callback_data": f"admin_reject_{submission_id}"},
        ]]
    }
def tg_format_oldmarket_account(tg_user_id: int) -> str:
    link = UserTelegramLink.query.filter_by(tg_user_id=tg_user_id).first()
    if not link:
        return (
            "👤 <b>Аккаунт в OldMarket</b>\n\n"
            "Telegram пока не привязан к аккаунту сайта.\n\n"
            "Для привязки зарегистрируйтесь на сайте и выполните команду:\n"
            "<code>/link CODE</code>"
        )

    user = User.query.get(link.user_id)
    if not user:
        return (
            "👤 <b>Аккаунт в OldMarket</b>\n\n"
            "Привязанный аккаунт не найден."
        )

    profile = UserProfile.query.filter_by(user_id=user.id).first()
    description = ""
    if profile and profile.description:
        description = profile.description.strip()

    return (
        "👤 <b>Аккаунт в OldMarket</b>\n\n"
        f"<b>Логин:</b> {user.username}\n"
        f"<b>Email:</b> {user.email}\n"
        f"<b>Дата создания:</b> {user.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"<b>Описание:</b> {description or '—'}"
    )
def tg_oldmarket_account_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🔑 Сбросить пароль", "callback_data": "om_reset_password"}],
            [{"text": "⬅️ Назад", "callback_data": "back_to_main"}],
        ]
    }
def tg_submission_text(submission: Submission, premium: bool = False) -> str:
    prefix = "💎 ПЛАТНАЯ ЗАЯВКА\n" if premium else ""
    return (
        f"{prefix}📱 <b>НОВАЯ ЗАЯВКА #{submission.id}</b>\n\n"
        f"👤 <b>Пользователь:</b> {submission.username or 'Unknown'} (ID: {submission.tg_user_id})\n"
        f"📛 <b>Название:</b> {submission.app_name}\n"
        f"🧑‍💻 <b>Автор:</b> {submission.author or '-'}\n"
        f"📝 <b>Описание:</b> {submission.description}\n"
        f"🔢 <b>Версия:</b> {submission.version}\n"
        f"🎯 <b>Тип:</b> {submission.app_type}\n"
        f"📂 <b>Категория:</b> {submission.category_label} ({submission.category_code})\n"
        f"📊 <b>Min Android:</b> {submission.min_android}\n"
        f"🔗 <b>APK:</b> {submission.apk_url}"
    )
def tg_send_submission_to_admin(submission_id: int):
    sub = Submission.query.get(submission_id)
    if not sub or not TG_ADMIN_ID:
        return
    caption = tg_submission_text(sub, premium=is_tg_premium(sub.tg_user_id))
    kb = tg_submission_admin_keyboard(sub.id)
    if sub.icon_path and os.path.exists(sub.icon_path):
        tg_send_photo(TG_ADMIN_ID, sub.icon_path, caption=caption, reply_markup=kb)
    else:
        tg_send_message(TG_ADMIN_ID, caption, kb)
    screens = [x for x in (sub.screenshots or "").split(",") if x]
    if screens:
        tg_send_media_group(TG_ADMIN_ID, screens)
def tg_stats_text() -> str:
    total = Submission.query.count()
    pending = Submission.query.filter_by(status='pending').count()
    approved = Submission.query.filter_by(status='approved').count()
    rejected = Submission.query.filter_by(status='rejected').count()
    return (
        "📊 Статистика заявок:\n\n"
        f"Всего заявок: {total}\n"
        f"⏳ Ожидают: {pending}\n"
        f"✅ Одобрены: {approved}\n"
        f"❌ Отклонены: {rejected}"
    )
def tg_reset_submission_state(user_id: int):
    submission_states.pop(int(user_id), None)
    submission_cache.pop(int(user_id), None)
def tg_resolve_username(msg_from: dict) -> str:
    username = (msg_from or {}).get("username")
    if username:
        return f"@{username}"
    return (msg_from or {}).get("first_name") or "Unknown"
def delete_review_full(review_id: int):
    ReviewReaction.query.filter_by(review_id=review_id).delete()
    ReviewComment.query.filter_by(review_id=review_id).delete()
    ReactionRateLimit.query.filter_by(review_id=review_id).delete()
    CommentRateLimit.query.filter_by(review_id=review_id).delete()
    ReactionIP.query.filter_by(review_id=review_id).delete()
    Review.query.filter_by(id=review_id).delete()
    db.session.commit()
def ban_user_and_purge(user_id: int):
    reviews = Review.query.filter_by(user_id=user_id).all()
    review_ids = [r.id for r in reviews]
    if review_ids:
        ReviewReaction.query.filter(ReviewReaction.review_id.in_(review_ids)).delete(synchronize_session=False)
        ReviewComment.query.filter(ReviewComment.review_id.in_(review_ids)).delete(synchronize_session=False)
        ReactionRateLimit.query.filter(ReactionRateLimit.review_id.in_(review_ids)).delete(synchronize_session=False)
        CommentRateLimit.query.filter(CommentRateLimit.review_id.in_(review_ids)).delete(synchronize_session=False)
        ReactionIP.query.filter(ReactionIP.review_id.in_(review_ids)).delete(synchronize_session=False)
    Review.query.filter_by(user_id=user_id).delete()
    ReviewReaction.query.filter_by(user_id=user_id).delete()
    ReviewComment.query.filter_by(user_id=user_id).delete()
    UserProfile.query.filter_by(user_id=user_id).delete()
    Download.query.filter_by(user_id=user_id).delete()
    User.query.filter_by(id=user_id).delete()
    db.session.commit()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    if request.path.startswith('/html/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

@app.route('/api/app/<int:app_id>', methods=['GET', 'OPTIONS'])
def api_app(app_id):
    if request.method == 'OPTIONS':
        return '', 200
    app_item = next((a for a in apps if a["id"] == app_id), None)
    if not app_item:
        return jsonify({"error": "App not found"}), 404
    avg_rating, review_count = db.session.query(
        func.avg(Review.rating),
        func.count(Review.id)
    ).filter(Review.app_id == app_id).one()
    downloads = db.session.query(func.count(Download.id)) \
                          .filter(Download.app_id == app_id) \
                          .scalar() or 0
    return jsonify({
        **app_item,
        "rating": round(float(avg_rating or 0.0), 1),
        "downloads": int(downloads),
        "review_count": int(review_count or 0)
    })
@app.route('/api/apps', methods=['GET', 'OPTIONS'])
def api_apps():
    if request.method == 'OPTIONS':
        return '', 200
    is_game = request.args.get('is_game')
    category = (request.args.get('category') or '').strip()
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int, default=0)
    filtered = apps
    if is_game is not None:
        want_game = str(is_game).lower() in ('1', 'true', 'yes')
        filtered = [a for a in apps if bool(a.get('is_game')) == want_game]
    if category:
        filtered = [a for a in filtered if _category_code_for_app(a) == category]
    if limit is not None and limit > 0:
        filtered = filtered[offset:offset + limit]
    return jsonify(build_apps_with_stats(filtered))
@app.route('/api/apps/search', methods=['GET', 'OPTIONS'])
def api_apps_search():
    if request.method == 'OPTIONS':
        return '', 200
    q = (request.args.get('q') or '').strip()
    is_game = request.args.get('is_game')
    category = (request.args.get('category') or '').strip()
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int, default=0)
    filtered = apps
    if is_game is not None:
        want_game = str(is_game).lower() in ('1', 'true', 'yes')
        filtered = [a for a in filtered if bool(a.get('is_game')) == want_game]
    if category:
        filtered = [a for a in filtered if _category_code_for_app(a) == category]
    if q:
        qn = _norm(q)
        terms = [t for t in qn.split(' ') if t]
        scored = []
        for a in filtered:
            hay = _app_search_haystack(a)
            if all(t in hay for t in terms):
                scored.append((a, _search_score(a, terms)))
        scored.sort(key=lambda x: (x[1], x[0].get('id', 0)), reverse=True)
        filtered = [a for a, _ in scored]
    if limit is not None and limit > 0:
        filtered = filtered[offset:offset + limit]
    return jsonify(build_apps_with_stats(filtered))

@app.route('/api/categories', methods=['GET', 'OPTIONS'])
def api_categories():
    if request.method == 'OPTIONS':
        return '', 200
    is_game = request.args.get('is_game')
    if is_game is None:
        return jsonify({
            "apps": [{"code": code, "label": label, "is_game": False} for code, label in APP_CATEGORY_CHOICES],
            "games": [{"code": code, "label": label, "is_game": True} for code, label in GAME_CATEGORY_CHOICES]
        })
    want_game = str(is_game).lower() in ('1', 'true', 'yes')
    source = GAME_CATEGORY_CHOICES if want_game else APP_CATEGORY_CHOICES
    return jsonify([{"code": code, "label": label, "is_game": want_game} for code, label in source])

@app.route('/api/category/<string:category_code>/apps', methods=['GET', 'OPTIONS'])
def api_category_apps(category_code):
    if request.method == 'OPTIONS':
        return '', 200

    category_code = (category_code or '').strip()
    if not category_code:
        return jsonify({"error": "Category not found"}), 404

    app_map, game_map, all_map = _category_label_maps()
    is_game = None
    if category_code in app_map:
        is_game = False
        label = app_map[category_code]
    elif category_code in game_map:
        is_game = True
        label = game_map[category_code]
    elif category_code in all_map:
        label = all_map[category_code]
    else:
        return jsonify({"error": "Category not found"}), 404

    filtered = [a for a in apps if _category_code_for_app(a) == category_code]
    if is_game is None and filtered:
        is_game = bool(filtered[0].get('is_game'))
    if is_game is None:
        is_game = False

    filtered = [a for a in filtered if bool(a.get('is_game')) == is_game]
    return jsonify({
        "category": {
            "code": category_code,
            "label": label,
            "is_game": is_game
        },
        "apps": build_apps_with_stats(filtered)
    })

@app.route('/api/top-apps', methods=['GET', 'OPTIONS'])
def top_apps():
    if request.method == 'OPTIONS':
        return '', 200
    non_games = [a for a in apps if not a.get('is_game')]
    with_stats = build_apps_with_stats(non_games)
    top_list = sorted(with_stats, key=lambda x: x['downloads'], reverse=True)[:10]
    return jsonify(top_list)
@app.route('/api/top-games', methods=['GET', 'OPTIONS'])
def top_games():
    if request.method == 'OPTIONS':
        return '', 200
    games = [a for a in apps if a.get('is_game')]
    with_stats = build_apps_with_stats(games)
    top_list = sorted(with_stats, key=lambda x: x['downloads'], reverse=True)[:10]
    return jsonify(top_list)
@app.route("/html/banners/<path:filename>")
def banners_download(filename):
    return send_from_directory(BANNERS_DIR, filename)
@app.route("/api/banners")
def api_banners():
    link_map = {
        "banner1.jpg": "https://t.me/assizdns",
        "banner2.jpg": "",
        "banner6.jpg": "https://t.me/oldmarketsupport_bot",
        "banner4.jpg": "https://yoomoney.ru/to/4100117591116914",
        "banner5.jpg": "https://t.me/apksherr",
        "banner7.jpg": "https://t.me/oldsoftcavebackup"
    }
    items = []
    for fn in sorted(os.listdir(BANNERS_DIR)):
        low = fn.lower()
        if not (low.endswith(".jpg") or low.endswith(".jpeg") or low.endswith(".png") or low.endswith(".webp")):
            continue
        items.append({
            "image": fn,
            "url": link_map.get(fn, "")
        })
    return items
@app.route('/api/app/<int:app_id>/screenshots', methods=['GET', 'OPTIONS'])
def get_app_screenshots(app_id):
    if request.method == 'OPTIONS':
        return '', 200
    app_item = next((a for a in apps if a["id"] == app_id), None)
    if not app_item:
        return jsonify({"error": "App not found"}), 404
    return jsonify(app_item.get("screenshots", []))
@app.route('/html/screenshots/<path:filename>')
def serve_screenshots(filename):
    return send_from_directory('html/screenshots', filename)
@app.route('/api/app/<int:app_id>/versions', methods=['GET', 'OPTIONS'])
def get_app_versions(app_id):
    if request.method == 'OPTIONS':
        return '', 200
    app_item = next((a for a in apps if a["id"] == app_id), None)
    if not app_item:
        return jsonify({"error": "App not found"}), 404
    return jsonify(app_item.get("versions", []))

@app.route('/api/download/<int:app_id>/<version>', methods=['GET', 'OPTIONS'])
def download_app_version(app_id, version):
    if request.method == 'OPTIONS':
        return '', 200

    try:
        app_data = next((a for a in apps if a["id"] == app_id), None)
        if not app_data:
            return jsonify({"error": "App not found"}), 404

        version_data = next((v for v in app_data.get("versions", []) if v["version"] == version), None)
        if not version_data:
            return jsonify({"error": "Version not found"}), 404

        user_id = request.args.get('user_id', type=int)
        user_ip = get_real_ip()

        if is_ip_blocked(user_ip):
            log_security("download_blocked_ip", ip=user_ip, details=f"app_id={app_id}")
            return jsonify({"error": "IP blocked"}), 429

        try:
            record_download_once(app_id=app_id, user_id=user_id, user_ip=user_ip)
        except DatabaseError as e:
            return jsonify({
                "error": "Database is corrupted",
                "details": str(e)
            }), 500

        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            version_data["apk_file"],
            as_attachment=True
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
@app.route('/api/download/<int:app_id>', methods=['GET', 'OPTIONS'])
def download_app(app_id):
    if request.method == 'OPTIONS':
        return '', 200

    try:
        user_id = request.args.get('user_id', type=int)
        app_data = next((a for a in apps if a["id"] == app_id), None)
        if not app_data:
            return jsonify({"error": "App not found"}), 404

        user_ip = get_real_ip()

        if is_ip_blocked(user_ip):
            log_security("download_blocked_ip", ip=user_ip, details=f"app_id={app_id}")
            return jsonify({"error": "IP blocked"}), 429

        try:
            record_download_once(app_id=app_id, user_id=user_id, user_ip=user_ip)
        except DatabaseError as e:
            return jsonify({
                "error": "Database is corrupted",
                "details": str(e)
            }), 500

        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            app_data["apk_file"],
            as_attachment=True
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/app/<int:app_id>/reviews', methods=['GET', 'OPTIONS'])
def get_reviews(app_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        viewer_id = request.args.get('viewer_id', type=int)
        reviews = (Review.query
                   .filter_by(app_id=app_id)
                   .order_by(Review.created_at.desc())
                   .all())
        if not reviews:
            return jsonify([])
        review_ids = [r.id for r in reviews]
        user_ids = list({r.user_id for r in reviews})
        users = User.query.filter(User.id.in_(user_ids)).all()
        users_map = {u.id: u for u in users}
        profiles = UserProfile.query.filter(UserProfile.user_id.in_(user_ids)).all()
        profiles_map = {p.user_id: p for p in profiles}
        react_rows = (db.session.query(
                        ReviewReaction.review_id.label('rid'),
                        func.sum(case((ReviewReaction.value == 1, 1), else_=0)).label('likes'),
                        func.sum(case((ReviewReaction.value == -1, 1), else_=0)).label('dislikes'),
                      )
                      .filter(ReviewReaction.review_id.in_(review_ids))
                      .group_by(ReviewReaction.review_id)
                      .all())
        reacts_map = {row.rid: row for row in react_rows}
        viewer_map = {}
        if viewer_id:
            vr = (ReviewReaction.query
                  .filter(ReviewReaction.user_id == viewer_id,
                          ReviewReaction.review_id.in_(review_ids))
                  .all())
            viewer_map = {x.review_id: x.value for x in vr}
        c_rows = (db.session.query(
                    ReviewComment.review_id.label('rid'),
                    func.count(ReviewComment.id).label('cnt')
                  )
                  .filter(ReviewComment.review_id.in_(review_ids))
                  .group_by(ReviewComment.review_id)
                  .all())
        comments_cnt_map = {row.rid: row.cnt for row in c_rows}
        result = []
        for r in reviews:
            u = users_map.get(r.user_id)
            p = profiles_map.get(r.user_id)
            rx = reacts_map.get(r.id)
            likes = int(rx.likes) if rx else 0
            dislikes = int(rx.dislikes) if rx else 0
            result.append({
                "id": r.id,
                "user_id": r.user_id,
                "username": u.username if u else "Unknown",
                "avatar": (p.avatar if p else "default_avatar.png"),
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "likes": likes,
                "dislikes": dislikes,
                "user_reaction": int(viewer_map.get(r.id, 0)) if viewer_id else 0,
                "comments_count": int(comments_cnt_map.get(r.id, 0)),
                "is_premium": int(p.is_premium) if p else 0,
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/app/<int:app_id>/review', methods=['POST', 'OPTIONS'])
def add_review(app_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        ip = data.get("ip") or request.headers.get("X-Forwarded-For") or request.remote_addr
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
        if is_ip_blocked(ip):
            log_security("review_blocked_ip", ip=ip, details=f"app_id={app_id}")
            return jsonify({"error": "IP blocked"}), 429
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 401
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401
        rating = data.get('rating')
        if not rating:
            return jsonify({"error": "Rating is required"}), 400
        app_exists = any(a['id'] == app_id for a in apps)
        if not app_exists:
            return jsonify({"error": "App not found"}), 404
        existing_review = Review.query.filter_by(app_id=app_id, user_id=user_id).first()
        if existing_review:
            return jsonify({"error": "You have already reviewed this app"}), 400
        review = Review(
            app_id=app_id,
            user_id=user_id,
            rating=rating,
            comment=data.get('comment', '')
        )
        db.session.add(review)
        db.session.commit()
        return jsonify({"success": True, "message": "Review added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/review/<int:review_id>/reaction', methods=['POST', 'OPTIONS'])
def set_review_reaction(review_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        ip = get_real_ip()
        if is_ip_blocked(ip):
            return jsonify({"error": "IP blocked"}), 429
        data = request.get_json() or {}
        user_id = data.get('user_id')
        value = int(data.get('value', 0))
        if not user_id:
            return jsonify({"error": "User ID is required"}), 401
        if value not in (-1, 0, 1):
            return jsonify({"error": "Invalid value"}), 400
        review = Review.query.get(review_id)
        if not review:
            return jsonify({"error": "Review not found"}), 404
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=60)
        ip_events = ReactionRateLimit.query.filter(
            ReactionRateLimit.ip == ip,
            ReactionRateLimit.created_at >= cutoff
        ).count()
        if ip_events >= 20:
            ban_ip(ip, reason="reaction_rate_limit", hours=1)
            return jsonify({"error": "Too many reactions, IP temporarily blocked"}), 429
        db.session.add(ReactionRateLimit(ip=ip, review_id=review_id))
        db.session.commit()
        ip_exists = ReactionIP.query.filter_by(review_id=review_id, ip=ip).first()
        if ip_exists:
            return jsonify({"error": "Only one reaction per IP for this review"}), 429
        if value == 0:
            return jsonify({"error": "Cannot remove reaction"}), 400
        existing = ReviewReaction.query.filter_by(review_id=review_id, user_id=user_id).first()
        if existing:
            existing.value = value
        else:
            db.session.add(ReviewReaction(review_id=review_id, user_id=user_id, value=value))
        db.session.add(ReactionIP(review_id=review_id, ip=ip))
        db.session.commit()
        likes = ReviewReaction.query.filter_by(review_id=review_id, value=1).count()
        dislikes = ReviewReaction.query.filter_by(review_id=review_id, value=-1).count()
        return jsonify({"success": True, "likes": likes, "dislikes": dislikes, "user_reaction": value})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/review/<int:review_id>/comments', methods=['GET', 'OPTIONS'])
def list_review_comments(review_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        review = Review.query.get(review_id)
        if not review:
            return jsonify({"error": "Review not found"}), 404
        rows = (db.session.query(
                    ReviewComment,
                    User.username,
                    UserProfile.avatar
                )
                .join(User, User.id == ReviewComment.user_id)
                .outerjoin(UserProfile, UserProfile.user_id == ReviewComment.user_id)
                .filter(ReviewComment.review_id == review_id)
                .order_by(ReviewComment.created_at.asc())
                .all())
        out = []
        for c, username, avatar in rows:
            out.append({
                "id": c.id,
                "user_id": c.user_id,
                "username": username or "Unknown",
                "avatar": avatar or "default_avatar.png",
                "text": c.text,
                "created_at": c.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/review/<int:review_id>/comment', methods=['POST', 'OPTIONS'])
def add_review_comment(review_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        ip = get_real_ip()
        if is_ip_blocked(ip):
            return jsonify({"error": "IP blocked"}), 429
        data = request.get_json() or {}
        user_id = data.get('user_id')
        text_ = (data.get('text') or '').strip()
        if not user_id:
            return jsonify({"error": "User ID is required"}), 401
        if not text_:
            return jsonify({"error": "Text is required"}), 400
        if len(text_) > 300:
            return jsonify({"error": "Comment too long (max 300)"}), 400
        review = Review.query.get(review_id)
        if not review:
            return jsonify({"error": "Review not found"}), 404
        allowed_re = r'^[a-zA-Zа-яА-ЯёЁ0-9\s!()\?.,:;\"\'\+\-]+$'
        if not re.match(allowed_re, text_):
            return jsonify({"error": "Invalid characters"}), 400
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=2)
        cnt_ip = CommentRateLimit.query.filter(
            CommentRateLimit.ip == ip,
            CommentRateLimit.created_at >= cutoff
        ).count()
        if cnt_ip >= 10:
            return jsonify({"error": "Слишком много комментариев. Попробуйте позже."}), 429
        cutoff2 = now - timedelta(seconds=15)
        cnt_pair = CommentRateLimit.query.filter(
            CommentRateLimit.user_id == int(user_id),
            CommentRateLimit.review_id == review_id,
            CommentRateLimit.created_at >= cutoff2
        ).count()
        if cnt_pair >= 1:
            return jsonify({"error": "Слишком часто. Подождите 15 секунд."}), 429
        db.session.add(CommentRateLimit(ip=ip, user_id=int(user_id), review_id=review_id))
        db.session.commit()
        db.session.add(ReviewComment(review_id=review_id, user_id=user_id, text=text_))
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/review/<int:review_id>/report', methods=['POST', 'OPTIONS'])
def report_review(review_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 401
        reporter = User.query.get(int(user_id))
        if not reporter:
            return jsonify({"error": "User not found"}), 401
        review = Review.query.get(review_id)
        if not review:
            return jsonify({"error": "Review not found"}), 404
        app_id = int(review.app_id)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        exists = Report.query.filter(
            Report.review_id == review_id,
            Report.reporter_user_id == int(user_id),
            Report.created_at >= cutoff
        ).first()
        if exists:
            return jsonify({"error": "You have already reported this review recently"}), 429
        reason = (data.get("reason") or "").strip()
        if reason and len(reason) > 200:
            reason = reason[:200]
        rep = Report(
            review_id=review_id,
            reporter_user_id=int(user_id),
            reason=reason or None
        )
        db.session.add(rep)
        db.session.commit()
        author = User.query.get(review.user_id)
        review_text = _trim200(review.comment or "")
        author_name = author.username if author else f"User#{review.user_id}"
        text_msg = (
            f"🚨 <b>ЖАЛОБА НА ОТЗЫВ</b>\n"
            f"<b>Приложение:</b> #{app_id}\n"
            f"<b>ID отзыва:</b> {review.id}\n"
            f"<b>Кто пожаловался:</b> {reporter.username} (user_id={reporter.id})\n"
            f"<b>Автор отзыва:</b> {author_name} (user_id={review.user_id})\n"
            f"<b>Рейтинг:</b> {review.rating}\n"
            f"<b>Текст:</b> {review_text or '(без текста)'}\n"
        )
        if rep.reason:
            text_msg += f"<b>Причина:</b> {rep.reason}\n"
        kb = {
            "inline_keyboard": [
                [
                    {"text": "🗑 Удалить отзыв", "callback_data": f"rep|{rep.id}|del"},
                    {"text": "⛔ Забанить пользователя", "callback_data": f"rep|{rep.id}|banq"},
                ],
                [
                    {"text": "✅ Игнорировать", "callback_data": f"rep|{rep.id}|ign"}
                ]
            ]
        }
        mods = TgModerator.query.filter(
            (TgModerator.app_id == None) | (TgModerator.app_id == app_id)
        ).all()
        print("REPORT DEBUG app_id=", app_id, "report_id=", rep.id, "mods=", len(mods), "admin=", TG_ADMIN_ID)
        if not mods:
            if TG_ADMIN_ID:
                tg_send_message(TG_ADMIN_ID, text_msg, kb)
        else:
            sent_to = set()
            for m in mods:
                if m.tg_user_id in sent_to:
                    continue
                sent_to.add(m.tg_user_id)
                tg_send_message(m.tg_user_id, text_msg, kb)
        return jsonify({"success": True})
    except Exception as e:
        print("REPORT ERROR:", repr(e))
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/<int:user_id>/telegram-link', methods=['GET', 'OPTIONS'])
def get_user_telegram_link_status(user_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        link = UserTelegramLink.query.filter_by(user_id=user_id).first()
        if link:
            return jsonify({
                "linked": True,
                "tg_username": link.tg_username,
                "tg_user_id": link.tg_user_id
            }), 200

        cleanup_pending_user_tg_links()
        pending = PendingUserTelegramLink.query.filter(
            PendingUserTelegramLink.user_id == user_id,
            PendingUserTelegramLink.is_finished == False,
            PendingUserTelegramLink.expires_at > datetime.utcnow()
        ).order_by(PendingUserTelegramLink.created_at.desc()).first()

        return jsonify({
            "linked": False,
            "code": pending.code if pending else None,
            "expires_at": pending.expires_at.strftime('%Y-%m-%d %H:%M:%S') if pending else None
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/user/<int:user_id>/telegram-link/start', methods=['POST', 'OPTIONS'])
def start_user_telegram_link(user_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        cleanup_pending_user_tg_links()

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        existing = UserTelegramLink.query.filter_by(user_id=user_id).first()
        if existing:
            return jsonify({
                "error": "Telegram already linked",
                "linked": True,
                "tg_username": existing.tg_username,
                "tg_user_id": existing.tg_user_id
            }), 400

        old_pending = PendingUserTelegramLink.query.filter(
            PendingUserTelegramLink.user_id == user_id,
            PendingUserTelegramLink.is_finished == False
        ).first()
        if old_pending:
            db.session.delete(old_pending)
            db.session.commit()

        code = generate_link_code()
        while PendingUserTelegramLink.query.filter_by(code=code).first() or PendingTelegramRegistration.query.filter_by(code=code).first():
            code = generate_link_code()

        pending = PendingUserTelegramLink(
            code=code,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        db.session.add(pending)
        db.session.commit()

        return jsonify({
            "success": True,
            "linked": False,
            "code": code,
            "expires_in_minutes": 30
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/register/start', methods=['POST', 'OPTIONS'])
def register_start():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        cleanup_pending_tg_regs()

        data = request.get_json() or {}

        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()
        password = data.get('password') or ''

        ip = get_real_ip()

        if is_ip_blocked(ip):
            return jsonify({"error": "IP blocked"}), 429

        if not check_registration_rate_limit(ip):
            return jsonify({"error": "Too many registrations from this IP today"}), 429

        if not username or not email or not password:
            return jsonify({"error": "All fields are required"}), 400

        if len(username) < 3 or len(username) > 15:
            return jsonify({"error": "Логин должен быть от 3 до 15 символов"}), 400

        if not re.match(r'^[a-zA-Z0-9]+$', username):
            return jsonify({"error": "Логин может содержать только латинские буквы и цифры"}), 400

        uname_lower = username.lower()
        for bw in BAD_WORDS:
            if bw.lower() in uname_lower:
                return jsonify({"error": "Логин содержит запрещённые слова"}), 400

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({"error": "Некорректный email"}), 400

        if len(password) < 4:
            return jsonify({"error": "Пароль должен быть от 4 символов"}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 400

        old_pending = PendingTelegramRegistration.query.filter(
            PendingTelegramRegistration.created_ip == ip,
            PendingTelegramRegistration.is_finished == False
        ).first()
        if old_pending:
            db.session.delete(old_pending)
            db.session.commit()

        code = generate_link_code()
        while PendingTelegramRegistration.query.filter_by(code=code).first():
            code = generate_link_code()

        pending = PendingTelegramRegistration(
            code=code,
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            created_ip=ip,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        db.session.add(pending)
        db.session.commit()

        return jsonify({
            "success": True,
            "code": code,
            "expires_in_minutes": 30
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/register/status', methods=['POST', 'OPTIONS'])
def register_status():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json() or {}
        code = (data.get('code') or '').strip()

        if not code:
            return jsonify({"error": "Code is required"}), 400

        pending = PendingTelegramRegistration.query.filter_by(code=code).first()
        if not pending:
            return jsonify({"error": "Код не найден"}), 404

        if pending.expires_at < datetime.utcnow():
            return jsonify({"error": "Код истёк"}), 410

        return jsonify({
            "success": True,
            "is_linked": bool(pending.is_linked),
            "is_finished": bool(pending.is_finished)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/register/finish', methods=['POST', 'OPTIONS'])
def register_finish():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json() or {}
        code = (data.get('code') or '').strip()

        if not code:
            return jsonify({"error": "Code is required"}), 400

        pending = PendingTelegramRegistration.query.filter_by(code=code).first()
        if not pending:
            return jsonify({"error": "Код не найден"}), 404

        if pending.expires_at < datetime.utcnow():
            return jsonify({"error": "Код истёк"}), 410

        if not pending.is_linked or not pending.tg_user_id:
            return jsonify({"error": "Telegram ещё не привязан"}), 400

        if pending.is_finished:
            return jsonify({"error": "Регистрация уже завершена"}), 400

        if User.query.filter_by(username=pending.username).first():
            return jsonify({"error": "Username already exists"}), 400

        if User.query.filter_by(email=pending.email).first():
            return jsonify({"error": "Email already exists"}), 400

        tg_lock = TelegramAccountLock.query.filter_by(tg_user_id=pending.tg_user_id).first()
        if tg_lock:
            return jsonify({"error": "Этот Telegram уже использовался для регистрации"}), 403

        user = User(
            username=pending.username,
            email=pending.email,
            password_hash=pending.password_hash,
            last_login_ip=None
        )
        db.session.add(user)
        db.session.commit()

        db.session.add(UserTelegramLink(
            user_id=user.id,
            tg_user_id=pending.tg_user_id,
            tg_username=pending.tg_username
        ))

        db.session.add(TelegramAccountLock(
            tg_user_id=pending.tg_user_id,
            tg_username=pending.tg_username,
            first_user_id=user.id,
            first_username=user.username,
            is_consumed=True
        ))

        pending.is_finished = True
        db.session.commit()

        increment_registration_ip(get_real_ip())
        log_security("register_success_tg_linked", ip=get_real_ip(), user_id=user.id, details=f"tg_user_id={pending.tg_user_id}")

        return jsonify({
            "success": True,
            "user_id": user.id,
            "username": user.username
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()
        password = (data.get('password') or '')
        ip = get_real_ip()
        if is_ip_blocked(ip):
            log_security("register_blocked_ip", ip=ip)
            return jsonify({"error": "IP blocked"}), 429
        if not check_registration_rate_limit(ip):
            log_security("register_rate_limit", ip=ip, details="too many accounts from this IP today")
            return jsonify({"error": "Too many registrations from this IP today"}), 429
        if not username or not email or not password:
            return jsonify({"error": "All fields are required"}), 400
        if len(username) < 3 or len(username) > 32:
            return jsonify({"error": "Username must be between 3 and 32 chars"}), 400
        if not re.match(r'^[a-zA-Z0-9_\-]+$', username):
            return jsonify({"error": "Username contains invalid characters"}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({"error": "Invalid email"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 400
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            last_login_ip=None
        )
        db.session.add(user)
        db.session.commit()
        increment_registration_ip(ip)
        log_security("register_success", ip=ip, user_id=user.id)
        return jsonify({
            "message": "User created successfully",
            "user_id": user.id,
            "username": user.username
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '')
        ip = get_real_ip()
        if is_ip_blocked(ip):
            log_security("login_blocked_ip", ip=ip, details=f"username={username}")
            return jsonify({"error": "IP blocked"}), 429
        if check_login_bruteforce(ip):
            ban_ip(ip, reason='login_bruteforce', hours=1)
            log_security("login_bruteforce_block", ip=ip, details=f"username={username}")
            return jsonify({"error": "Too many failed attempts, IP temporarily blocked"}), 429
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            user.last_login_ip = ip
            db.session.commit()
            record_login_attempt(ip, username, True)
            log_security("login_success", ip=ip, user_id=user.id)
            return jsonify({"success": True, "user_id": user.id, "username": user.username}), 200
        record_login_attempt(ip, username, False)
        log_security("login_failed", ip=ip, details=f"username={username}")
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/<int:user_id>/profile', methods=['GET', 'OPTIONS'])
def get_user_profile(user_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)
            db.session.commit()
        return jsonify({
            "user_id": user.id,
            "username": user.username,
            "avatar": profile.avatar,
            "description": profile.description,
            "created_at": user.created_at.strftime('%Y-%m-%d'),
            "is_premium": profile.is_premium,
            "premium_until": profile.premium_until.strftime('%Y-%m-%d') if profile.premium_until else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/user/<int:user_id>/profile', methods=['PUT', 'OPTIONS'])
def update_user_profile(user_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)
        if 'avatar' in data and data['avatar'] in AVAILABLE_AVATARS:
            profile.avatar = data['avatar']
        if 'description' in data:
            if len(data['description']) > 200:
                return jsonify({"error": "Description too long"}), 400
            profile.description = data['description']
        db.session.commit()
        return jsonify({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/avatars', methods=['GET', 'OPTIONS'])
def get_avatars():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify(AVAILABLE_AVATARS)
@app.route('/html/avatars/<path:filename>')
def serve_avatars(filename):
    return send_from_directory('html/avatars', filename)

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        total_downloads = Download.query.count()
        total_users = User.query.count()
        total_reviews = Review.query.count()
        return jsonify({
            "total_downloads": total_downloads,
            "total_users": total_users,
            "total_reviews": total_reviews
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/html/apps/<path:filename>')
def serve_apps_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/client/analytics/summary', methods=['GET', 'OPTIONS'])
def analytics_summary():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        rows = db.session.query(
            ClientAnalytics.api_level,
            ClientAnalytics.android_version,
            func.count(ClientAnalytics.id).label("records"),
            func.sum(ClientAnalytics.hits).label("hits")
        ).group_by(
            ClientAnalytics.api_level,
            ClientAnalytics.android_version
        ).order_by(ClientAnalytics.api_level.asc()).all()

        return jsonify([
            {
                "api_level": int(r.api_level),
                "android_version": r.android_version,
                "count": int(r.records or 0),
                "hits": int(r.hits or 0)
            }
            for r in rows
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/client/latest")
def client_latest():
    return get_client_update()

@app.route('/api/client/analytics', methods=['POST', 'OPTIONS'])
def api_client_analytics():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        api_level = int(data.get('api_level') or 0)
        if api_level <= 0:
            return jsonify({"error": "api_level is required"}), 400

        ip = get_real_ip()
        app_version_code = int(data.get('app_version_code') or 0)
        app_version_name = str(data.get('app_version_name') or '')[:50]
        device_model = str(data.get('device_model') or '')[:120]
        manufacturer = str(data.get('manufacturer') or '')[:120]
        lang = str(data.get('lang') or '')[:10]
        android_version = api_level_to_android(api_level)
        now = datetime.utcnow()

        rec = ClientAnalytics.query.filter_by(
            ip=ip,
            api_level=api_level,
            app_version_code=app_version_code,
            device_model=device_model,
            manufacturer=manufacturer,
            lang=lang
        ).first()

        if rec:
            rec.last_seen_at = now
            rec.hits = int(rec.hits or 0) + 1
            if app_version_name:
                rec.app_version_name = app_version_name
        else:
            rec = ClientAnalytics(
                ip=ip,
                api_level=api_level,
                android_version=android_version,
                app_version_code=app_version_code,
                app_version_name=app_version_name,
                device_model=device_model,
                manufacturer=manufacturer,
                lang=lang,
                created_at=now,
                last_seen_at=now,
                hits=1
            )
            db.session.add(rec)
        db.session.commit()
        return jsonify({"success": True, "android_version": android_version})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/client/analytics/summary', methods=['GET', 'OPTIONS'])
def api_client_analytics_summary():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        rows = db.session.query(
            ClientAnalytics.api_level,
            ClientAnalytics.android_version,
            func.count(ClientAnalytics.id).label("records"),
            func.sum(ClientAnalytics.hits).label("hits")
        ).group_by(
            ClientAnalytics.api_level,
            ClientAnalytics.android_version
        ).order_by(ClientAnalytics.api_level.asc()).all()
        return jsonify({
            "items": [{
                "api_level": int(r.api_level),
                "android_version": r.android_version,
                "records": int(r.records or 0),
                "hits": int(r.hits or 0)
            } for r in rows]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _tg_get_updates(offset=None, timeout=30):
    if not TG_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/getUpdates"
    payload = {"timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    try:
        r = requests.get(url, params=payload, timeout=timeout+5)
        return r.json()
    except Exception as e:
        print("getUpdates error:", e)
        return None
def _process_telegram_update(upd: dict):
    try:
        if "callback_query" in upd:
            cq = upd["callback_query"]
            cq_id = cq.get("id")
            from_id = int(cq.get("from", {}).get("id", 0) or 0)
            msg = cq.get("message") or {}
            chat_id = int((msg.get("chat") or {}).get("id", 0) or 0)
            message_id = int(msg.get("message_id", 0) or 0)
            data = cq.get("data") or ""

            with app.app_context():
                if data == "submit_app":
                    tg_answer_callback(cq_id)
                    submission_states[from_id] = STATE_APP_NAME
                    submission_cache[from_id] = {"screenshots": []}
                    tg_edit_message(chat_id, message_id, "📱 Давайте добавим ваше приложение.\n\nВведите название приложения:", reply_markup=tg_with_cancel([[{"text": "⬅️ Назад", "callback_data": "back_to_main"}]]))
                    return

                if data == "om_account":
                    tg_answer_callback(cq_id)
                    tg_edit_message(chat_id, message_id, tg_format_oldmarket_account(from_id), reply_markup=tg_oldmarket_account_keyboard())
                    return

                if data == "om_reset_password":
                    tg_answer_callback(cq_id)
                    link = UserTelegramLink.query.filter_by(tg_user_id=from_id).first()
                    if not link:
                        tg_edit_message(chat_id, message_id, "❌ Этот Telegram не привязан к аккаунту OldMarket.", reply_markup={"inline_keyboard": [[{"text": "⬅️ Назад", "callback_data": "back_to_main"}]]})
                        return
                    account_password_reset_waiting[from_id] = True
                    tg_edit_message(chat_id, message_id, "🔑 <b>Смена пароля</b>\n\nВведите новый пароль сообщением.\nМинимум 6 символов.", reply_markup={"inline_keyboard": [[{"text": "⬅️ Назад", "callback_data": "om_account"}]]})
                    return

                if data == "donate":
                    tg_answer_callback(cq_id)
                    tg_edit_message(chat_id, message_id, "💸 Поддержать проект\n\nВыберите удобный способ:", reply_markup={"inline_keyboard": [[{"text": "🟠 DALink", "url": DONATE_URL_1}], [{"text": "🟣 YooMoney", "url": DONATE_URL_2}], [{"text": "⬅️ Назад", "callback_data": "back_to_main"}]]})
                    return

                if data == "ad_banner":
                    tg_answer_callback(cq_id)
                    tg_edit_message(chat_id, message_id, "Холст рекламы 16:9. Аренда — 50₽ на 2 недели.\nПо поводу аренды писать: @slavch4k", reply_markup={"inline_keyboard": [[{"text": "⬅️ Назад", "callback_data": "back_to_main"}]]})
                    return

                if data == "paid_add":
                    tg_answer_callback(cq_id)
                    rec = TgPremium.query.filter_by(tg_user_id=from_id).first()
                    if rec and rec.expire_at > datetime.utcnow():
                        days_left = max(0, (rec.expire_at - datetime.utcnow()).days)
                        premium_text = (
                            "⭐ Премиум подписка\n\nСтатус: Активна\n"
                            f"Истекает: {rec.expire_at.strftime('%Y-%m-%d %H:%M')} (UTC)\n"
                            f"Осталось дней: {days_left}\n\n"
                            "Премиум даёт:\n• Добавление вашего приложения в течение дня в OldMarket"
                        )
                    elif rec:
                        premium_text = "⚠️ Ваша премиум-подписка истекла.\nВы можете продлить её, написав: @slavch4k\n\nСтоимость: 50₽ на 7 дней"
                    else:
                        premium_text = "⭐ Премиум подписка\n\nПремиум подписка даёт:\n• Добавление вашего приложения в течение дня в OldMarket\n\nСтоимость: 50₽ на 7 дней\n\nДля покупки — напишите администратору: @slavch4k"
                    tg_edit_message(chat_id, message_id, premium_text, reply_markup={"inline_keyboard": [[{"text": "⬅️ Назад", "callback_data": "back_to_main"}]]})
                    return

                if data == "stats":
                    tg_answer_callback(cq_id)
                    if from_id != TG_ADMIN_ID:
                        tg_edit_message(chat_id, message_id, "❌ У вас нет доступа к этой команде")
                        return
                    tg_edit_message(chat_id, message_id, tg_stats_text(), reply_markup={"inline_keyboard": [[{"text": "⬅️ Назад", "callback_data": "back_to_main"}]]})
                    return

                if data == "back_to_main":
                    tg_answer_callback(cq_id)
                    submission_states[from_id] = None
                    submission_cache[from_id] = {}
                    reject_reason_waiting.pop(from_id, None)
                    account_password_reset_waiting.pop(from_id, None)
                    tg_edit_message(chat_id, message_id, "🤖 Главное меню\n\nВыберите действие:", reply_markup=tg_main_keyboard(from_id))
                    return

                if data == "cancel_submission":
                    tg_answer_callback(cq_id)
                    tg_reset_submission_state(from_id)
                    tg_edit_message(chat_id, message_id, "❌ Процесс предложки отменён.", reply_markup=tg_main_keyboard(from_id))
                    return

                if data.startswith("type_"):
                    tg_answer_callback(cq_id)
                    submission_cache.setdefault(from_id, {"screenshots": []})["app_type"] = "Игра" if data == "type_game" else "Приложение"
                    submission_states[from_id] = STATE_CATEGORY
                    tg_edit_message(chat_id, message_id, "📂 Выберите категорию:", reply_markup=tg_category_keyboard())
                    return

                if data.startswith("cat_"):
                    tg_answer_callback(cq_id)
                    code = data.split("_", 1)[1]
                    label = next((l for c, l in CATEGORY_CHOICES if c == code), code)
                    submission_cache.setdefault(from_id, {"screenshots": []})["category_code"] = code
                    submission_cache[from_id]["category_label"] = label
                    submission_states[from_id] = STATE_MIN_ANDROID
                    tg_edit_message(chat_id, message_id, "📊 Выберите минимальную версию Android:", reply_markup=tg_api_keyboard())
                    return

                if data.startswith("minapi_"):
                    tg_answer_callback(cq_id)
                    api_code = data.split("_", 1)[1]
                    label = next((l for c, l in API_CHOICES if c == api_code), f"API {api_code}")
                    submission_cache.setdefault(from_id, {"screenshots": []})["min_android"] = label
                    submission_states[from_id] = STATE_SCREENSHOTS
                    tg_edit_message(chat_id, message_id, "📸 Пришлите скриншоты (по желанию).", reply_markup=tg_screens_keyboard())
                    return

                if data in ("skip_screens", "done_screens"):
                    tg_answer_callback(cq_id)
                    submission_states[from_id] = STATE_APK_URL
                    tg_edit_message(chat_id, message_id, "🔗 Введите ссылку на APK файл.\nЖелательно брать APK из проверенных источников, например: Trashbox, 4PDA, APKPure, Internet Archive.", reply_markup=tg_with_cancel([]))
                    return

                if data.startswith("admin_approve_"):
                    if from_id != TG_ADMIN_ID:
                        tg_answer_callback(cq_id, "Нет прав")
                        return
                    tg_answer_callback(cq_id)
                    submission_id = int(data.split("_")[2])
                    sub = Submission.query.get(submission_id)
                    if not sub:
                        tg_edit_message(chat_id, message_id, "❌ Заявка не найдена.")
                        return
                    sub.status = "approved"
                    db.session.commit()
                    try:
                        tg_send_message(sub.tg_user_id, f"Ваше приложение «{sub.app_name}» было одобрено.")
                    except Exception as e:
                        print("approve notify error:", e)
                    tg_edit_message(chat_id, message_id, f"✅ ЗАЯВКА #{submission_id} ОДОБРЕНА")
                    tg_edit_reply_markup(chat_id, message_id, None)
                    return

                if data.startswith("admin_reject_"):
                    if from_id != TG_ADMIN_ID:
                        tg_answer_callback(cq_id, "Нет прав")
                        return
                    tg_answer_callback(cq_id)
                    submission_id = int(data.split("_")[2])
                    reject_reason_waiting[from_id] = submission_id
                    tg_send_message(chat_id, "📝 Укажите причину отклонения заявки:", reply_markup={"inline_keyboard": [[{"text": "❌ Отмена", "callback_data": "cancel_reject"}]]})
                    return

                if data == "cancel_reject":
                    tg_answer_callback(cq_id)
                    reject_reason_waiting.pop(from_id, None)
                    tg_edit_message(chat_id, message_id, "❌ Отклонение отменено")
                    return

                if data.startswith("rep|"):
                    parts = data.split("|")
                    if len(parts) != 3:
                        tg_answer_callback(cq_id, "Неизвестная кнопка")
                        return
                    report_id = int(parts[1])
                    action = parts[2]
                    rep = Report.query.get(report_id)
                    if not rep:
                        tg_answer_callback(cq_id, "Жалоба не найдена")
                        return
                    review = Review.query.get(rep.review_id)
                    allowed = False
                    if from_id == TG_ADMIN_ID:
                        allowed = True
                    elif review:
                        app_id = int(review.app_id)
                        mod = TgModerator.query.filter(TgModerator.tg_user_id == from_id, ((TgModerator.app_id == None) | (TgModerator.app_id == app_id))).first()
                        allowed = bool(mod)
                    if not allowed:
                        tg_answer_callback(cq_id, "Нет прав")
                        return
                    if action == "del":
                        if review:
                            delete_review_full(review.id)
                        rep.status = "resolved"
                        rep.handled_by_tg = from_id
                        rep.handled_action = "delete"
                        db.session.commit()
                        tg_answer_callback(cq_id, "Отзыв удалён")
                        tg_edit_message(chat_id, message_id, "✅ Жалоба обработана: <b>отзыв удалён</b>", reply_markup={"inline_keyboard": []})
                        return
                    if action == "banq":
                        tg_answer_callback(cq_id, "Подтвердите бан")
                        tg_edit_message(chat_id, message_id, "⚠️ <b>Вы действительно хотите забанить пользователя?</b>\nЭто удалит пользователя и все его отзывы/комментарии.", reply_markup={"inline_keyboard": [[{"text": "✅ Да, забанить", "callback_data": f"rep|{rep.id}|ban2"}, {"text": "↩️ Отмена", "callback_data": f"rep|{rep.id}|ign"}]]})
                        return
                    if action == "ban2":
                        if review:
                            ban_user_and_purge(review.user_id)
                        rep.status = "resolved"
                        rep.handled_by_tg = from_id
                        rep.handled_action = "ban"
                        db.session.commit()
                        tg_answer_callback(cq_id, "Пользователь удалён + контент очищен")
                        tg_edit_message(chat_id, message_id, "⛔ Жалоба обработана: <b>пользователь удалён + контент очищен</b>", reply_markup={"inline_keyboard": []})
                        return
                    if action == "ign":
                        rep.status = "ignored"
                        rep.handled_by_tg = from_id
                        rep.handled_action = "ignore"
                        db.session.commit()
                        tg_answer_callback(cq_id, "Игнорировано")
                        tg_edit_message(chat_id, message_id, "✅ Жалоба обработана: <b>игнор</b>", reply_markup={"inline_keyboard": []})
                        return

                tg_answer_callback(cq_id, "Неизвестная кнопка")
                return

        if "message" in upd:
            msg = upd["message"]
            from_user = msg.get("from") or {}
            from_id = int(from_user.get("id", 0) or 0)
            chat_id = int((msg.get("chat") or {}).get("id", 0) or 0)
            text_ = (msg.get("text") or "").strip()
            state = submission_states.get(from_id)

            if account_password_reset_waiting.get(from_id):
                new_password = text_.strip()
                if text_.startswith("/"):
                    tg_send_message(chat_id, "❌ Введите новый пароль обычным сообщением.")
                    return
                if len(new_password) < 6:
                    tg_send_message(chat_id, "❌ Пароль должен быть не короче 6 символов.")
                    return
                with app.app_context():
                    link = UserTelegramLink.query.filter_by(tg_user_id=from_id).first()
                    if not link:
                        account_password_reset_waiting.pop(from_id, None)
                        tg_send_message(chat_id, "❌ Этот Telegram не привязан к аккаунту сайта.")
                        return
                    user = User.query.get(link.user_id)
                    if not user:
                        account_password_reset_waiting.pop(from_id, None)
                        tg_send_message(chat_id, "❌ Аккаунт сайта не найден.")
                        return
                    user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                account_password_reset_waiting.pop(from_id, None)
                tg_send_message(chat_id, "✅ Пароль успешно изменён.", tg_oldmarket_account_keyboard())
                return

            with app.app_context():
                if text_.startswith("/"):
                    if text_ == "/start":
                        tg_reset_submission_state(from_id)
                        tg_send_message(chat_id, "Добро пожаловать в бот для предложки приложений.\n\nЗдесь вы можете предложить своё приложение для добавления в OldMarket.\nДля отмены предложки используйте кнопку «Отмена» или команду /cancel.\nИнформацию об APK файле удобнее смотреть здесь: https://sisik.eu/apk-tool\n\nВыберите действие:", tg_main_keyboard(from_id))
                        return
                    if text_ == "/cancel":
                        tg_reset_submission_state(from_id)
                        reject_reason_waiting.pop(from_id, None)
                        account_password_reset_waiting.pop(from_id, None)
                        tg_send_message(chat_id, "❌ Процесс предложки отменён.", tg_main_keyboard(from_id))
                        return
                    if text_ == "/mypremium":
                        rec = TgPremium.query.filter_by(tg_user_id=from_id).first()
                        if not rec:
                            tg_send_message(chat_id, "У вас нет премиум-подписки.\n\nПремиум даёт:\n• Добавление вашего приложения в течение дня в OldMarket\n\nДля покупки — напишите администратору: @slavch4k")
                            return
                        if rec.expire_at <= datetime.utcnow():
                            tg_send_message(chat_id, "⚠️ Ваша премиум-подписка истекла.\nВы можете продлить её, написав администратору: @slavch4k")
                            return
                        days_left = max(0, (rec.expire_at - datetime.utcnow()).days)
                        tg_send_message(chat_id, f"⭐ Премиум-подписка\n\nСтатус: Активна\nИстекает: {rec.expire_at.strftime('%Y-%m-%d %H:%M')} (UTC)\nОсталось дней: {days_left}")
                        return
                    if text_.startswith("/link"):
                        parts = text_.split()
                        if len(parts) != 2:
                            tg_send_message(chat_id, "Использование: /link 123456")
                            return
                        code = parts[1].strip()

                        existing_link = UserTelegramLink.query.filter_by(tg_user_id=from_id).first()
                        if existing_link:
                            tg_send_message(chat_id, "❌ Этот Telegram уже привязан к аккаунту OldMarket.")
                            return

                        pending = PendingTelegramRegistration.query.filter_by(code=code).first()
                        if pending:
                            if pending.expires_at < datetime.utcnow():
                                tg_send_message(chat_id, "❌ Код истёк. Начните регистрацию заново на сайте.")
                                return
                            if pending.is_finished:
                                tg_send_message(chat_id, "❌ Этот код уже использован.")
                                return
                            lock = TelegramAccountLock.query.filter_by(tg_user_id=from_id).first()
                            if lock:
                                tg_send_message(chat_id, "❌ Этот Telegram-аккаунт уже использовался для регистрации и больше не может быть использован повторно.")
                                return
                            pending.tg_user_id = from_id
                            pending.tg_username = from_user.get("username")
                            pending.is_linked = True
                            db.session.commit()
                            tg_send_message(chat_id, "✅ Telegram успешно привязан.\nТеперь вернитесь на сайт и нажмите кнопку «Проверить привязку».")
                            return

                        pending_existing = PendingUserTelegramLink.query.filter_by(code=code).first()
                        if pending_existing:
                            if pending_existing.expires_at < datetime.utcnow():
                                tg_send_message(chat_id, "❌ Код истёк. Сгенерируйте новый код в профиле сайта.")
                                return
                            if pending_existing.is_finished:
                                tg_send_message(chat_id, "❌ Этот код уже использован.")
                                return
                            if UserTelegramLink.query.filter_by(user_id=pending_existing.user_id).first():
                                tg_send_message(chat_id, "❌ У этого аккаунта уже привязан Telegram.")
                                return

                            db.session.add(UserTelegramLink(
                                user_id=pending_existing.user_id,
                                tg_user_id=from_id,
                                tg_username=from_user.get("username")
                            ))
                            pending_existing.tg_user_id = from_id
                            pending_existing.tg_username = from_user.get("username")
                            pending_existing.is_finished = True
                            db.session.commit()
                            tg_send_message(chat_id, "✅ Telegram успешно привязан к вашему аккаунту OldMarket.")
                            return

                        tg_send_message(chat_id, "❌ Код не найден.")
                        return
                    if text_ == "/resetpass":
                        link = UserTelegramLink.query.filter_by(tg_user_id=from_id).first()
                        if not link:
                            tg_send_message(chat_id, "❌ Этот Telegram не привязан к аккаунту сайта.")
                            return
                        account_password_reset_waiting[from_id] = True
                        tg_send_message(chat_id, "🔑 Введите новый пароль сообщением.\nМинимум 6 символов.")
                        return

                    parts = text_.split()
                    cmd = parts[0]
                    if from_id == TG_ADMIN_ID:
                        if cmd == "/givepremium":
                            if len(parts) < 3:
                                tg_send_message(chat_id, "Использование:\n/givepremium user_id дни")
                                return
                            try:
                                target_id = int(parts[1])
                                days = int(parts[2])
                            except ValueError:
                                tg_send_message(chat_id, "user_id и дни должны быть числами.")
                                return
                            expire = set_tg_premium(target_id, days)
                            tg_send_message(chat_id, f"Премиум выдан пользователю {target_id} на {days} дней.\nДо: {expire.strftime('%Y-%m-%d %H:%M')} (UTC)")
                            return
                        if cmd == "/delpremium":
                            if len(parts) < 2:
                                tg_send_message(chat_id, "Использование:\n/delpremium user_id")
                                return
                            try:
                                target_id = int(parts[1])
                            except ValueError:
                                tg_send_message(chat_id, "user_id должен быть числом.")
                                return
                            clear_tg_premium(target_id)
                            tg_send_message(chat_id, f"Премиум снят с пользователя {target_id}.")
                            return
                        if cmd == "/addmod":
                            if len(parts) < 2:
                                tg_send_message(chat_id, "Использование: /addmod <tg_id> [app_id]")
                                return
                            try:
                                tg_id = int(parts[1])
                                app_id = int(parts[2]) if len(parts) >= 3 else None
                            except ValueError:
                                tg_send_message(chat_id, "tg_id и app_id должны быть числами.")
                                return
                            ex = TgModerator.query.filter_by(tg_user_id=tg_id, app_id=app_id).first()
                            if not ex:
                                db.session.add(TgModerator(tg_user_id=tg_id, app_id=app_id))
                                db.session.commit()
                            tg_send_message(chat_id, f"Ок. Модератор {tg_id} добавлен " + (f"для app_id={app_id}" if app_id is not None else "глобально"))
                            return
                        if cmd == "/delmod":
                            if len(parts) < 2:
                                tg_send_message(chat_id, "Использование: /delmod <tg_id> [app_id]")
                                return
                            try:
                                tg_id = int(parts[1])
                                app_id = int(parts[2]) if len(parts) >= 3 else None
                            except ValueError:
                                tg_send_message(chat_id, "tg_id и app_id должны быть числами.")
                                return
                            TgModerator.query.filter_by(tg_user_id=tg_id, app_id=app_id).delete()
                            db.session.commit()
                            tg_send_message(chat_id, f"Ок. Модератор {tg_id} удалён " + (f"для app_id={app_id}" if app_id is not None else "глобально"))
                            return
                        if cmd == "/mods":
                            rows = TgModerator.query.order_by(TgModerator.tg_user_id.asc()).all()
                            if not rows:
                                tg_send_message(chat_id, "Модераторов нет.")
                                return
                            lines = [f"{r.tg_user_id} — " + (f"app_id={r.app_id}" if r.app_id is not None else "global") for r in rows]
                            tg_send_message(chat_id, "Модераторы:\n" + "\n".join(lines))
                            return
                        tg_send_message(chat_id, "Команды: /addmod /delmod /mods /givepremium /delpremium")
                        return

                    tg_send_message(chat_id, "Команды:\n/start\n/link CODE\n/resetpass\n/cancel")
                    return

                if from_id in reject_reason_waiting and text_:
                    submission_id = reject_reason_waiting.pop(from_id)
                    sub = Submission.query.get(submission_id)
                    if not sub:
                        tg_send_message(chat_id, "❌ Ошибка: не найдена заявка для отклонения")
                        return
                    sub.status = "rejected"
                    sub.reject_reason = text_
                    db.session.commit()
                    try:
                        tg_send_message(sub.tg_user_id, f"Ваше приложение «{sub.app_name}» было отклонено.\n\n📋 Причина: {text_}")
                    except Exception as e:
                        print("reject notify error:", e)
                    tg_send_message(chat_id, "✅ Заявка отклонена, пользователь уведомлён")
                    return

                if "document" in msg:
                    document = msg.get("document") or {}
                    file_id = document.get("file_id")
                    if state == STATE_ICON:
                        ext = os.path.splitext(document.get("file_name") or "")[1].lower()
                        if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
                            tg_send_message(chat_id, "❌ Пожалуйста, отправьте иконку PNG/JPG/JPEG/WebP", tg_with_cancel([]))
                            return
                        remote_path = tg_get_file(file_id)
                        if not remote_path:
                            tg_send_message(chat_id, "❌ Не удалось скачать иконку.")
                            return
                        filename = f"icons/{from_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                        if not tg_download_file(remote_path, filename):
                            tg_send_message(chat_id, "❌ Не удалось сохранить иконку.")
                            return
                        submission_cache.setdefault(from_id, {"screenshots": []})["icon_path"] = filename
                        submission_states[from_id] = STATE_VERSION
                        tg_send_message(chat_id, "✅ Иконка принята.\n\nВведите версию приложения:", tg_with_cancel([]))
                        return
                    if state == STATE_SCREENSHOTS:
                        remote_path = tg_get_file(file_id)
                        if not remote_path:
                            tg_send_message(chat_id, "❌ Не удалось скачать скриншот.", tg_screens_keyboard())
                            return
                        ext = os.path.splitext(document.get("file_name") or "")[1].lower() or ".jpg"
                        filename = f"screens/{from_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                        if not tg_download_file(remote_path, filename):
                            tg_send_message(chat_id, "❌ Не удалось сохранить скриншот.", tg_screens_keyboard())
                            return
                        submission_cache.setdefault(from_id, {"screenshots": []}).setdefault("screenshots", []).append(filename)
                        tg_send_message(chat_id, "🖼️ Скриншот добавлен. Можете прислать ещё или нажмите «Готово/Пропустить».", tg_screens_keyboard())
                        return

                if msg.get("photo"):
                    photos = msg.get("photo") or []
                    file_id = photos[-1].get("file_id") if photos else None
                    if file_id:
                        remote_path = tg_get_file(file_id)
                        if not remote_path:
                            tg_send_message(chat_id, "❌ Не удалось скачать изображение.")
                            return
                        if state == STATE_ICON:
                            filename = f"icons/{from_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            if not tg_download_file(remote_path, filename):
                                tg_send_message(chat_id, "❌ Не удалось сохранить иконку.")
                                return
                            submission_cache.setdefault(from_id, {"screenshots": []})["icon_path"] = filename
                            submission_states[from_id] = STATE_VERSION
                            tg_send_message(chat_id, "✅ Иконка принята.\n\nВведите версию приложения:", tg_with_cancel([]))
                            return
                        if state == STATE_SCREENSHOTS:
                            filename = f"screens/{from_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            if not tg_download_file(remote_path, filename):
                                tg_send_message(chat_id, "❌ Не удалось сохранить скриншот.", tg_screens_keyboard())
                                return
                            submission_cache.setdefault(from_id, {"screenshots": []}).setdefault("screenshots", []).append(filename)
                            tg_send_message(chat_id, "🖼️ Скриншот добавлен. Можете прислать ещё или нажмите «Готово/Пропустить».", tg_screens_keyboard())
                            return

                if not text_:
                    return
                if not state:
                    tg_send_message(chat_id, "Выберите действие:", tg_main_keyboard(from_id))
                    return

                cache = submission_cache.setdefault(from_id, {"screenshots": []})
                if state == STATE_APP_NAME:
                    cache["app_name"] = text_.strip()
                    submission_states[from_id] = STATE_AUTHOR
                    tg_send_message(chat_id, "👤 Укажите автора приложения:", tg_with_cancel([]))
                    return
                if state == STATE_AUTHOR:
                    cache["author"] = text_.strip()
                    submission_states[from_id] = STATE_DESCRIPTION
                    tg_send_message(chat_id, "📝 Введите описание приложения:", tg_with_cancel([]))
                    return
                if state == STATE_DESCRIPTION:
                    cache["description"] = text_.strip()
                    submission_states[from_id] = STATE_ICON
                    tg_send_message(chat_id, "🖼️ Отправьте иконку приложения.", tg_with_cancel([]))
                    return
                if state == STATE_VERSION:
                    cache["version"] = text_.strip()
                    submission_states[from_id] = STATE_APP_TYPE
                    tg_send_message(chat_id, "Выберите тип:", tg_app_type_keyboard())
                    return
                if state == STATE_APK_URL:
                    if not (text_.startswith("http://") or text_.startswith("https://")):
                        tg_send_message(chat_id, "❌ Пожалуйста, введите корректную ссылку (http:// или https://)", tg_with_cancel([]))
                        return
                    cache["apk_url"] = text_.strip()
                    required = ["app_name", "author", "description", "version", "app_type", "category_code", "category_label", "min_android", "icon_path"]
                    missing = [f for f in required if not cache.get(f)]
                    if missing:
                        tg_send_message(chat_id, "❌ Ошибка: отсутствуют поля: " + ", ".join(missing), tg_with_cancel([]))
                        return
                    sub = Submission(
                        tg_user_id=from_id,
                        username=tg_resolve_username(from_user),
                        app_name=cache["app_name"],
                        author=cache["author"],
                        description=cache["description"],
                        icon_path=cache["icon_path"],
                        version=cache["version"],
                        app_type=cache["app_type"],
                        category_code=cache["category_code"],
                        category_label=cache["category_label"],
                        min_android=cache["min_android"],
                        apk_url=cache["apk_url"],
                        screenshots=",".join(cache.get("screenshots", [])),
                    )
                    db.session.add(sub)
                    db.session.commit()
                    tg_send_submission_to_admin(sub.id)
                    tg_reset_submission_state(from_id)
                    tg_send_message(chat_id, "✅ Ваше приложение отправлено на модерацию.\nВы получите уведомление, когда администратор проверит его.", tg_main_keyboard(from_id))
                    return
    except Exception as e:
        print("process update error:", repr(e))

telegram_polling_started = False

def tg_edit_reply_markup(chat_id: int, message_id: int, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return tg_api("editMessageReplyMarkup", payload)

def start_telegram_polling():
    global telegram_polling_started

    if telegram_polling_started:
        print("[TG] Polling already started, skip")
        return

    telegram_polling_started = True

    if not TG_BOT_TOKEN:
        print("[TG] TG_BOT_TOKEN is empty, polling disabled")
        return

    print("[TG] Polling started (local mode).")
    offset = None

    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/deleteWebhook",
            json={"drop_pending_updates": True},
            timeout=10
        )
    except Exception:
        pass

    while True:
        data = _tg_get_updates(offset=offset, timeout=25)
        if not data or not data.get("ok"):
            time.sleep(2)
            continue

        results = data.get("result") or []
        for upd in results:
            offset = (upd.get("update_id") or 0) + 1
            _process_telegram_update(upd)

        time.sleep(0.2)

def _table_columns(table: str) -> set[str]:
    rows = db.session.execute(text(f"PRAGMA table_info({table});")).fetchall()
    return {r[1] for r in rows}
def _table_exists(table: str) -> bool:
    row = db.session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table}
    ).fetchone()
    return row is not None
def ensure_schema_migrations():
    db.create_all()
    if _table_exists("user"):
        cols = _table_columns("user")
        if "last_login_ip" not in cols:
            db.session.execute(text("ALTER TABLE user ADD COLUMN last_login_ip VARCHAR(50);"))
            db.session.commit()
            print("[MIGRATION] Added user.last_login_ip")
    if not _table_exists("pending_user_telegram_link"):
        PendingUserTelegramLink.__table__.create(db.engine)
        print("[MIGRATION] Created pending_user_telegram_link")


    if not _table_exists("client_analytics"):
        ClientAnalytics.__table__.create(db.engine)
        print("[MIGRATION] Created client_analytics")
    if _table_exists("user_profile"):
        cols = _table_columns("user_profile")
        if "is_premium" not in cols:
            db.session.execute(text("ALTER TABLE user_profile ADD COLUMN is_premium INTEGER DEFAULT 0;"))
            db.session.commit()
            print("[MIGRATION] Added user_profile.is_premium")
        if "premium_until" not in cols:
            db.session.execute(text("ALTER TABLE user_profile ADD COLUMN premium_until DATETIME;"))
            db.session.commit()
            print("[MIGRATION] Added user_profile.premium_until")
        if "avatar" not in cols:
            db.session.execute(text("ALTER TABLE user_profile ADD COLUMN avatar VARCHAR(100) DEFAULT 'avatar1.png';"))
            db.session.commit()
            print("[MIGRATION] Added user_profile.avatar")
        if "description" not in cols:
            db.session.execute(text("ALTER TABLE user_profile ADD COLUMN description TEXT DEFAULT '';"))
            db.session.commit()
            print("[MIGRATION] Added user_profile.description")
def init_db():
    ensure_schema_migrations()
    if User.query.count() == 0:
        test_user = User(
            username="test",
            email="test@example.com",
            password_hash=generate_password_hash("test123")
        )
        db.session.add(test_user)
        db.session.commit()
if __name__ == '__main__':
    with app.app_context():
        init_db()
        print(f"Total downloads in database: {Download.query.count()}")
        db.session.execute(text("PRAGMA journal_mode=WAL;"))
        db.session.execute(text("PRAGMA foreign_keys=ON;"))
        db.session.commit()

    tg_thread = threading.Thread(
        target=start_telegram_polling,
        daemon=True
    )
    tg_thread.start()
    print("[TG] Telegram polling started")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
