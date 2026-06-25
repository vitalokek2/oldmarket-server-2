# Развёртывание OldMarket

## Порты

| Порт | Сервис | Назначение |
|------|--------|------------|
| 80   | nginx  | Фронтенд (раздаёт статику, прокси на 5000) |
| 5000 | FastAPI | API + HTML-страницы (Jinja2) |

Без nginx — всё на одном порту: `python -m uvicorn main:app --host 0.0.0.0 --port 5000`

---

## Структура файлов

### 🖥 Основной сервер (FastAPI + nginx)

```
/var/www/altmart/           # Корень проекта
├── main.py                 # FastAPI приложение
├── site_config.py          # Конфиг (название, пароль, CDN, ссылки)
├── apps_data.py            # Метаданные всех приложений
├── oldmarket.db            # SQLite база (создаётся сама)
├── requirements.txt        # Зависимости Python
├── nginx.conf              # nginx :80 → FastAPI :5000
├── start.sh                # Запуск всего сразу
│
├── templates/              # Jinja2 шаблоны (HTML)
│   ├── base.html
│   ├── index.html
│   ├── app.html
│   ├── login.html / register.html / profile.html
│   ├── categories.html / category.html / search.html
│   └── admin/
│       ├── login.html
│       ├── dashboard.html
│       └── edit.html
│
└── html/                   # Статические файлы (кроме ресурсов)
    ├── logo.png
    ├── favicon.ico
    ├── background.jpg
    ├── search.png / login.png / register.png / downloadclient.png
    └── appdownload/ / avatars/ (если на основном сервере)
```

### 📦 CDN / отдельный сервер для ресурсов

```
/var/www/cdn/               # Корень CDN (или отдельный сервер)
└── html/
    ├── apps/               # APK-файлы + иконки приложений
    │   ├── RootExplorer.apk
    │   ├── rootexplorer.png
    │   └── ...
    ├── screenshots/        # Скриншоты
    │   ├── scr1.png
    │   └── ...
    ├── banners/            # Баннеры
    │   ├── banner1.jpg
    │   └── ...
    └── avatars/            # Аватарки пользователей
        ├── avatar1.png
        └── ...
```

В `site_config.py` укажи:

```python
CDN = {
    "base_url": "https://cdn.example.com",
    ...
}
```

И nginx на CDN-сервере:
```nginx
server {
    listen 80;
    server_name cdn.example.com;
    root /var/www/cdn/html;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

---

## Быстрый старт (всё на одном сервере, без CDN)

```bash
pip install -r requirements.txt

# Вариант A — всё на 80 (нужен root)
sudo python -m uvicorn main:app --host 0.0.0.0 --port 80

# Вариант B — nginx:80 + FastAPI:5000
python -m uvicorn main:app --host 0.0.0.0 --port 5000 &
nginx -c /путь/до/nginx.conf
```

---

## Что куда копировать при деплое

### Если всё на одном сервере (без CDN):

```
scp -r * user@server:/var/www/altmart/
```

### Если ресурсы на отдельном CDN:

```bash
# 1. На основной сервер
scp main.py site_config.py apps_data.py requirements.txt nginx.conf user@server:/var/www/altmart/
scp -r templates/ user@server:/var/www/altmart/
scp -r html/ user@server:/var/www/altmart/  (без apps/ screenshots/ banners/)

# 2. На CDN-сервер
scp -r html/apps/ html/screenshots/ html/banners/ html/avatars/ user@cdn:/var/www/cdn/html/
```

Потом настроить `site_config.py` → указать `CDN["base_url"]`.
