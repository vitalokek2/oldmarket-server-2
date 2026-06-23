# AltMart Server v2 — Обновление

## Что добавлено по сравнению с оригинальным форком

### 1. Открытое добавление приложений (`/submit`)
- **Минимальная форма**: только APK + категория + описание
- **Автопарсинг APK**: извлекает `package`, `versionName`, `versionCode`, `minSdk`, `app_name`, иконку
- **Модерация**: заявки хранятся отдельно, админ одобряет через CLI

### 2. Продвинутый поиск (`/api/apps/search`)
- Поиск по **всем полям**: name, author, package, category, description, tags
- **Релевантность**: сортировка по весам (название → автор → пакет → категория → теги → описание)
- **Фильтры**: по категории и типу (приложение/игра) одновременно с поиском

### 3. Скачивание конкретной версии
- `/api/download/{app_id}` — последняя версия
- `/api/download/{app_id}/{version_code}` — конкретная версия

### 4. Проверка дублей отзывов
- Один пользователь = один отзыв на приложение

### 5. CLI модерация
```bash
altmart submissions list              # Список заявок
altmart submissions view --id 1       # Детали заявки
altmart submissions approve --id 1  # Одобрить
altmart submissions reject --id 1 --reason "..."  # Отклонить
```

## Установка

1. Установи зависимость:
   ```bash
   pip install python-multipart
   ```

2. Переинициализируй БД:
   ```bash
   python scripts/init_db.py
   ```

3. Запусти сервер:
   ```bash
   python main.py
   ```

## Структура файлов

```
routers/
  submissions.py    # Новый: форма + API модерации + парсинг APK
  apps.py           # Изменён: продвинутый поиск + скачивание версий
  reviews.py        # Изменён: проверка дублей отзывов
  users.py          # Без изменений
  system.py         # Без изменений
main.py             # + submissions.router + статика submissions
security.py         # + таблица submissions
cli.py              # + команды submissions
scripts/
  init_db.py        # + таблица submissions
```

## API Endpoints

| Endpoint | Описание |
|----------|----------|
| `GET /submit` | HTML-форма загрузки |
| `POST /submit` | Отправить заявку |
| `GET /api/submissions` | Список заявок (JSON) |
| `POST /api/submissions/{id}/approve` | Одобрить заявку |
| `POST /api/submissions/{id}/reject` | Отклонить заявку |
| `GET /api/apps/search?q=...&category=...&is_game=...` | Продвинутый поиск |
| `GET /api/download/{app_id}` | Скачать последнюю версию |
| `GET /api/download/{app_id}/{version_code}` | Скачать конкретную версию |

## Парсинг APK

Автоматически извлекает данные из AndroidManifest.xml:
- Если XML текстовый — парсит через ElementTree
- Если бинарный — fallback на `aapt` (если установлен Android SDK)
- Иконка извлекается из `res/mipmap-*/ic_launcher.png`
