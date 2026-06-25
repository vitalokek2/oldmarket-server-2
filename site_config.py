# ──────────────────────────────────────────────────────────
#  Конфигурация сайта — меняйте всё что выделено ниже
#  После изменений перезапустите сервер
# ──────────────────────────────────────────────────────────

SITE = {
    # Название магазина (заголовок страниц)
    "name": "OldMarket",

    # Описание (meta description)
    "description": "Магазин старых Android приложений и игр",

    # Год в футере (copyright)
    "year": "2025-2026",

    # Ссылка на логотип (путь относительно /html/)
    "logo": "/html/logo.png",

    # Favicon
    "favicon": "/html/favicon.ico",

    # Счётчик посетителей / analytics (пустая строка = отключено)
    "analytics_code": "",
}

LINKS = {
    # Ссылка на скачивание клиента (/clients — страница со списком APK)
    "download_client": "/clients",

    # Ссылки для донатов (сколько хочешь)
    "donate_urls": [
        "https://example.com",
    ],

    # Контакты для рекламы / премиума
    "ad_contact": "@slavch4k",
    "premium_contact": "@slavch4k",

    # Telegram бот поддержки (для регистрации / привязки)
    "support_bot": "https://t.me/oldmarketsupport_bot",

    # Надпись на кнопке скачать APK
    "install_button": "Установить",
    "install_button_en": "Install",
}

BANNER_LINKS = {
    "banner1.jpg": "https://t.me/assizdns",
    "banner2.jpg": "",
    "banner6.jpg": "https://t.me/oldmarketsupport_bot",
    "banner4.jpg": "https://yoomoney.ru/to/4100117591116914",
    "banner5.jpg": "https://t.me/apksherr",
    "banner7.jpg": "https://t.me/oldsoftcavebackup",
}

CDN = {
    # Адрес CDN/отдельного сервера для ресурсов
    # Пустая строка = всё локально (как сейчас)
    "base_url": "",  # e.g. "https://cdn.example.com"

    # Какие папки уходят на CDN
    "paths": ["/html/apps/", "/html/screenshots/", "/html/avatars/", "/html/banners/"],
}

ADMIN = {
    # Пароль для входа в админку
    "password": "passwd",

    # Разрешённые IP-адреса (пустое множество = любой IP)
    "allowed_ips": set(),

    # Секретный ключ для сессий админки
    "secret_key": "change-me-to-something-random",
}

# ────────────────────── не трогать ───────────────────────

def cdn_url(path: str) -> str:
    """Возвращает полный URL с CDN-префиксом, если настроен."""
    if CDN["base_url"]:
        return CDN["base_url"].rstrip("/") + "/" + path.lstrip("/")
    return path

def apply_config(templates_env):
    """Добавляет config в глобальные переменные Jinja2."""
    templates_env.env.globals["config"] = SITE
    templates_env.env.globals["links"] = LINKS
    templates_env.env.globals["t"] = lambda lang, ru, en: ru if lang == "ru" else en
    templates_env.env.globals["cdn"] = cdn_url
