import sys
import argparse
from pathlib import Path

def peek_tree(directory, extensions, file_handle, indent=""):
    try:
        items = sorted(list(directory.iterdir()), key=lambda x: (x.is_file(), x.name))
    except PermissionError:
        print(f"{indent}[Доступ запрещен]", file=file_handle)
        return

    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        child_indent = "    " if is_last else "│   "

        # Печатаем имя файла/папки
        print(f"{indent}{connector}{item.name}", file=file_handle)

        if item.is_dir():
            peek_tree(item, extensions, file_handle, indent + child_indent)
        elif item.is_file():
            if item.suffix.lower() in extensions:
                try:
                    content = item.read_text(encoding='utf-8').strip()
                    if content:
                        lines = content.splitlines()
                        print(f"{indent}{child_indent}    \"\"\"", file=file_handle)
                        for line in lines:
                            print(f"{indent}{child_indent}    {line}", file=file_handle)
                        print(f"{indent}{child_indent}    \"\"\"", file=file_handle)
                    else:
                        print(f"{indent}{child_indent}    (пустой файл)", file=file_handle)
                except Exception:
                    # Если не текстовый файл или другая кодировка
                    print(f"{indent}{child_indent}    [Ошибка: невозможно прочитать контент]", file=file_handle)

def main():
    parser = argparse.ArgumentParser(description="Tree-like viewer with file content preview.")
    parser.add_argument("path", type=str, help="Путь к директории")
    parser.add_argument("--save", type=str, help="Путь к файлу для сохранения результата")
    parser.add_argument("--ext", type=str, default=".json,.txt,.py,.md,.yaml,.yml", 
                        help="Список расширений через запятую (по умолчанию: .json,.txt,.py,.md,.yaml)")
    
    args = parser.parse_args()
    target_path = Path(args.path)
    allowed_exts = set(args.ext.split(','))

    if not target_path.exists():
        print(f"Ошибка: Путь {target_path} не существует.")
        return

    # Определяем, куда писать: в файл или в консоль
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            print(f"Анализ директории: {target_path.absolute()}\n", file=f)
            peek_tree(target_path, allowed_exts, f)
        print(f"Готово! Результат сохранен в: {args.save}")
    else:
        # Если выводим в консоль, переключаем кодировку для Windows, чтобы не было UnicodeEncodeError
        if sys.platform == "win32":
            sys.stdout.reconfigure(encoding='utf-8')
        peek_tree(target_path, allowed_exts, sys.stdout)

if __name__ == "__main__":
    main()