import sqlite3
import requests
import time
import json

# Данные оригинала (взяты из твоего дампа mitmproxy)
BASE_URL = "http://oldmarket.store:5000"
DB_PATH = "altmart.db"

# Прикидываемся старым Android-устройством, чтобы сервер ничего не заподозрил
HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 5.1.1; SM-J120F Build/LMY47X)",
    "Host": "oldmarket.store:5000",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip"
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS apps (id INTEGER PRIMARY KEY, is_game INTEGER, category_code TEXT, data JSON)')
    cursor.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, app_id INTEGER, user_id INTEGER, rating INTEGER, comment TEXT, data JSON)')
    conn.commit()
    return conn

def scrape_live_api():
    conn = init_db()
    cursor = conn.cursor()

    print(f"--- Подключаюсь к {BASE_URL} ---")

    # 1. Скачиваем ВСЕ приложения
    print("Скачиваю список приложений...")
    try:
        response = requests.get(f"{BASE_URL}/api/apps", headers=HEADERS)
        response.raise_for_status()
        apps_data = response.json()
        
        apps_count = 0
        app_ids = [] # Сохраним ID для скачивания отзывов
        
        for app in apps_data:
            app_id = app.get("id")
            if app_id:
                app_ids.append(app_id)
                is_game = 1 if app.get("is_game") else 0
                cat_code = app.get("category_code", "unknown")
                
                cursor.execute(
                    "INSERT OR REPLACE INTO apps (id, is_game, category_code, data) VALUES (?, ?, ?, ?)",
                    (app_id, is_game, cat_code, json.dumps(app, ensure_ascii=False))
                )
                apps_count += 1
                
        conn.commit()
        print(f"✅ Скачано приложений: {apps_count}")
        
    except Exception as e:
        print(f"❌ Ошибка при скачивании приложений: {e}")
        return

    # 2. Скачиваем отзывы для каждого приложения
    print("\nНачинаю скачивать отзывы")
    reviews_count = 0
    
    for app_id in app_ids:
        try:
            # Делаем паузу в 0.5 секунды между запросами (ОЧЕНЬ ВАЖНО!)
            #time.sleep(0.5) 
            
            res = requests.get(f"{BASE_URL}/api/app/{app_id}/reviews", headers=HEADERS)
            
            if res.status_code == 200:
                reviews_data = res.json()
                for rev in reviews_data:
                    cursor.execute(
                        "INSERT INTO reviews (app_id, user_id, rating, comment, data) VALUES (?, ?, ?, ?, ?)",
                        (app_id, rev.get("user_id"), rev.get("rating"), rev.get("comment"), json.dumps(rev, ensure_ascii=False))
                    )
                    reviews_count += 1
                
                print(f"Приложение {app_id}: скачано отзывов - {len(reviews_data)}")
            else:
                print(f"Приложение {app_id}: нет отзывов или ошибка ({res.status_code})")
                
        except Exception as e:
            print(f"⚠️ Ошибка на приложении {app_id}: {e}")

    conn.commit()
    conn.close()
    print(f"\n✅ Кража данных успешно завершена! Всего отзывов: {reviews_count}")

if __name__ == "__main__":
    scrape_live_api()
