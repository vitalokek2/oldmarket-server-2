#!/usr/bin/env python3
import os
import sys
import subprocess
import sqlite3
import tty
import termios

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from rich.prompt import Prompt
except ImportError:
    print("❌ Ошибка: Не установлена библиотека rich.")
    print("Выполни: pip install rich")
    sys.exit(1)

console = Console()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLI_SCRIPT = os.path.join(BASE_DIR, "cli.py")
DB_PATH = os.path.join(BASE_DIR, "altmart.db")

# ==========================================
# ЧТЕНИЕ КЛАВИАТУРЫ (ДЛЯ LINUX / ARCH)
# ==========================================
def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# ==========================================
# ПОЛУЧЕНИЕ ДАННЫХ О СИСТЕМЕ
# ==========================================
def get_system_info():
    try:
        res = subprocess.run(['systemctl', 'is-active', 'altmart.service'], capture_output=True, text=True)
        status = "[bold green]🟢 active[/]" if res.stdout.strip() == "active" else "[bold red]🔴 stopped[/]"
    except:
        status = "[bold yellow]⚠️ missing[/]"

    if not os.path.exists(DB_PATH):
        stats = "[bold red]No DB found[/]"
    else:
        try:
            conn = sqlite3.connect(DB_PATH)
            apps = conn.execute("SELECT COUNT(*) FROM apps").fetchone()[0]
            users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            conn.close()
            stats = f"[cyan]Apps:[/] {apps} | [cyan]Users:[/] {users}"
        except:
            stats = "[red]DB Error[/]"
    
    return f" Daemon: {status}  │  {stats}"

# ==========================================
# ДВИЖОК ЦЕНТРИРОВАННОГО ОКНА (ЦЕНТР ТЕРМИНАЛА)
# ==========================================

def centered_menu(title, choices):
    selected_index = 0
    box_width = 55

    while True:
        # 1. Формируем контент для меню
        sys_info = get_system_info()
        
        # ЗАМЕНИ СТРОКУ НИЖЕ (убрали [bold rule] и сделали красивую сплошную линию под размер рамки)
        content = f"[dim]{sys_info}[/dim]\n[dim]─────────────────────────────────────────────────[/dim]\n"
        
        for i, choice in enumerate(choices):
            if i == selected_index:
                content += f" [bold green]➔  {choice}[/bold green]\n"
            else:
                content += f"    [white]{choice}[/white]\n"

        # 2. Оборачиваем в рамку Panel
        panel = Panel(
            content.rstrip(),
            title=f"[bold cyan] {title} [/bold cyan]",
            border_style="bright_blue",
            width=box_width,
            padding=(1, 2)
        )

        # 3. Считаем размеры экрана для вертикального центрирования
        term_size = os.get_terminal_size()
        box_height = len(choices) + 6  # Высота контента внутри рамки
        v_padding = (term_size.lines - box_height) // 2

        # 4. Чистим экран и выводим ровно по центру
        os.system('clear')
        print("\n" * max(0, v_padding), end="")
        console.print(Align.center(panel))

        # 5. Считываем нажатие
        key = get_key()
        if key == '\x1b[A':  # Стрелочка ВВЕРХ
            selected_index = (selected_index - 1) % len(choices)
        elif key == '\x1b[B':  # Стрелочка ВНИЗ
            selected_index = (selected_index + 1) % len(choices)
        elif key in ('\n', '\r'):  # ENTER
            return choices[selected_index]
        elif key == '\x1b':  # ESC
            return "🔙 Назад"

def run_cli(*args):
    os.system('clear')
    console.print(f"\n[dim]Выполняется команда: altmart {' '.join(args)}[/dim]\n")
    subprocess.run([sys.executable, CLI_SCRIPT, *args])
    console.print("\n[bold yellow]Нажми Enter для возврата...[/bold yellow]")
    input()

# ==========================================
# ПОДМЕНЮ СИСТЕМЫ
# ==========================================
def menu_service():
    while True:
        act = centered_menu("Управление службой (Systemd)", [
            "▶️  Запустить сервер",
            "⏹️  Остановить сервер",
            "🔄  Перезапустить сервер",
            "🔧  Установить демона в систему",
            "🔙  Назад"
        ])
        if "Назад" in act: break
        if "Запустить" in act: run_cli("service", "start")
        elif "Остановить" in act: run_cli("service", "stop")
        elif "Перезапустить" in act: run_cli("service", "restart")
        elif "Установить" in act: run_cli("service", "install")

def menu_db():
    while True:
        act = centered_menu("Управление базой данных", [
            "📊  Показать статистику",
            "💾  Сделать резервную копию",
            "✨  Инициализировать структуру",
            "🔥  Полностью сбросить базу (WIPE)",
            "🔙  Назад"
        ])
        if "Назад" in act: break
        if "статистику" in act: run_cli("db", "stats")
        elif "копию" in act: run_cli("db", "backup")
        elif "Инициализировать" in act: run_cli("db", "init")
        elif "WIPE" in act: run_cli("db", "wipe")

def menu_apps():
    while True:
        act = centered_menu("Каталог приложений", [
            "📋  Список программ",
            "🎮  Список игр",
            "➕  Добавить приложение вручную",
            "🗑️  Удалить приложение по ID",
            "🔙  Назад"
        ])
        if "Назад" in act: break
        if "программ" in act: run_cli("app", "list", "--apps", "--limit", "30")
        elif "игр" in act: run_cli("app", "list", "--games", "--limit", "30")
        elif "Удалить" in act:
            os.system('clear')
            app_id = Prompt.ask("[bold red]Введите ID для удаления[/]")
            if app_id: run_cli("app", "remove", "--id", app_id)
        elif "Добавить" in act:
            os.system('clear')
            console.print("[bold cyan]Заполнение карточки приложения:[/]\n")
            app_id = Prompt.ask("ID приложения (цифры)")
            name = Prompt.ask("Название")
            pkg = Prompt.ask("Имя пакета (com.example.app)")
            is_game = Prompt.ask("Это игра?", choices=["0", "1"], default="0")
            cat = Prompt.ask("Категория (tools, arcade...)", default="tools")
            apk = Prompt.ask("Имя APK файла")
            if app_id and name:
                run_cli("app", "add", "--id", app_id, "--name", name, "--pkg", pkg, "--is-game", is_game, "--cat", cat, "--apk", apk)

def menu_users():
    while True:
        act = centered_menu("Управление аккаунтами", [
            "📜  Список пользователей",
            "➕  Создать новый аккаунт",
            "👑  Изменить Premium статус",
            "🔙  Назад"
        ])
        if "Назад" in act: break
        if "Список" in act: run_cli("user", "list")
        elif "Создать" in act:
            os.system('clear')
            uname = Prompt.ask("Введите логин")
            upass = Prompt.ask("Введите пароль")
            if uname and upass: run_cli("user", "create", "--name", uname, "--text-pass", upass)
        elif "Premium" in act:
            os.system('clear')
            uid = Prompt.ask("ID или Логин пользователя")
            status = Prompt.ask("Выдать (1) или забрать (0)?", choices=["0", "1"], default="1")
            if uid: run_cli("user", "premium", "--user-id", uid, "--status", status)

# ==========================================
# ГЛАВНЫЙ ЦИКЛ
# ==========================================
def main_menu():
    while True:
        choice = centered_menu("AltMart Master Dashboard", [
            "⚙️   Управление сервером",
            "🗄️   База данных SQLite",
            "📱   Каталог приложений",
            "👥   Пользователи",
            "📜   Живые логи (Live Logs)",
            "❌   Выход из панели"
        ])

        if "Выход" in choice:
            os.system('clear')
            console.print("[bold green]TUI закрыт. Служба работает в фоне.[/bold green]")
            break
        elif "сервером" in choice: menu_service()
        elif "База" in choice: menu_db()
        elif "Каталог" in choice: menu_apps()
        elif "Пользователи" in choice: menu_users()
        elif "Логи" in choice:
            os.system('clear')
            console.print("[bold yellow]Для выхода из логов нажмите Ctrl+C[/bold yellow]\n")
            try:
                subprocess.run(['journalctl', '-u', 'altmart.service', '-f', '-n', '50'])
            except KeyboardInterrupt:
                pass

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        os.system('clear')
        sys.exit(0)
