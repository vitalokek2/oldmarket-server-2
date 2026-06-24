import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

_DEFAULT_CONFIG = {
    "market": {
        "name": "AltMart",
        "tagline": "неофициальный форк в память об OldMarket",
        "accent_color": "#94ab3a",
        "accent_dark": "#7a8e30",
        "accent_light": "#b3c95c",
        "logo_emoji": "A",
        "favicon": ""
    },
    "limits": {
        "max_apk_size_mb": 200,
        "registration_per_ip_per_day": 3,
        "login_bruteforce_window_minutes": 15,
        "login_bruteforce_max_failures": 5,
        "ban_duration_hours": 1
    },
    "contacts": {
        "telegram": "",
        "support_email": "",
        "github": "",
        "website": ""
    },
    "features": {
        "open_submissions": True,
        "require_moderation": True,
        "allow_user_registration": True,
        "show_download_count": True
    }
}

_config_cache = None

def load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            # Merge with defaults
            config = _deep_merge(_DEFAULT_CONFIG.copy(), user_config)
            _config_cache = config
            return config
        except Exception as e:
            print(f"[Config] Ошибка загрузки config.json: {e}, использую defaults")

    _config_cache = _DEFAULT_CONFIG.copy()
    return _config_cache

def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base

def get_market_name() -> str:
    return load_config()["market"]["name"]

def get_market_tagline() -> str:
    return load_config()["market"]["tagline"]

def get_accent_color() -> str:
    return load_config()["market"]["accent_color"]

def get_limits() -> dict:
    return load_config()["limits"]

def get_contacts() -> dict:
    return load_config()["contacts"]

def get_features() -> dict:
    return load_config()["features"]

def reload_config():
    global _config_cache
    _config_cache = None
