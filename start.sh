#!/bin/sh
# Запуск: sh start.sh

echo "========================================"
echo " OldMarket Server"
echo "========================================"
echo ""
echo " FastAPI :5000  (API + HTML)"
echo " nginx   :80    (-> :5000)"
echo ""

# 1. FastAPI на 5000
python -m uvicorn main:app --host 0.0.0.0 --port 5000 &
echo "FastAPI запущен на :5000"

# 2. nginx на 80 (если установлен)
if command -v nginx >/dev/null 2>&1; then
    nginx -c "$(pwd)/nginx.conf"
    echo "nginx запущен на :80"
else
    echo ""
    echo "[WARNING] nginx не найден."
    echo "Сайт на http://localhost:5000"
    echo "Для порта 80: sudo python -m uvicorn main:app --port 80"
    echo ""
fi

echo "Сайт:    http://localhost:5000"
echo "Админка: http://localhost:5000/admin/"
wait
