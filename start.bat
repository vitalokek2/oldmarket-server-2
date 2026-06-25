@echo off
chcp 65001 >nul
title OldMarket Server
cd /d "%~dp0"

echo ========================================
echo  %CD%
echo ========================================
echo.
echo  Варианты запуска на Windows:
echo.
echo  1. python run_win.py           — порт 5000 (самый простой)
echo  2. python run_win.py --80      — порты 80 + 5000 (от админа)
echo  3. python -m uvicorn main:app --host 0.0.0.0 --port 5000
echo.
echo ========================================
echo.

python run_win.py
pause
