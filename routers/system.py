import os

from fastapi import APIRouter, Query

from database import fetch_all, BASE_DIR
from config import load_config

router = APIRouter(prefix="/api")

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

GAME_CODES = {
    "simulators", "puzzles", "arcade", "races", "action_games", "casual",
    "strategies", "table_games", "shooter", "horror", "adventures", "rpg",
    "survival", "sport", "card_games", "other_games",
}


@router.get("/categories")
async def get_categories(is_game: int = Query(None)):
    if is_game == 1:
        filtered = [(c, l) for c, l in CATEGORY_CHOICES if c in GAME_CODES]
    elif is_game == 0:
        filtered = [(c, l) for c, l in CATEGORY_CHOICES if c not in GAME_CODES]
    else:
        filtered = CATEGORY_CHOICES
    return [{"code": code, "label": label} for code, label in filtered]


@router.get("/config")
async def get_config():
    return load_config()


AVAILABLE_AVATARS = [
    'avatar1.png', 'avatar2.png', 'avatar3.png', 'avatar4.png',
    'avatar5.gif', 'avatar6.gif', 'avatar7.gif', 'avatar8.gif',
    'avatar9.gif', 'avatar10.gif', 'avatar11.gif', 'avatar12.gif',
    'avatar13.gif', 'avatar14.gif', 'avatar15.gif', 'avatar16.gif',
    'avatar17.gif',
]


@router.get("/avatars")
async def get_avatars():
    avatars_dir = os.path.join(BASE_DIR, "downloaded", "html", "avatars")
    if os.path.isdir(avatars_dir):
        files = [f for f in os.listdir(avatars_dir) if f.endswith(('.png', '.gif'))]
        if files:
            return sorted(files)
    return AVAILABLE_AVATARS


@router.get("/client/latest")
async def get_latest_client():
    return {
        "notes_en": "Self-hosted Server is Running!",
        "notes_ru": "Твой личный сервер запущен и работает!",
        "update_url": "http://127.0.0.1:5000/apks/OldMarket2_3.apk",
        "version_code": 13,
        "version_name": "2.3",
    }
