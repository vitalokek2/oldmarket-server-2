"""
Запуск на Windows (без nginx).

Порты:
  :80  → простой реверс-прокси (перенаправляет на :5000)
  :5000 → FastAPI (API + HTML-страницы)

Запуск:
  python run_win.py          # :5000 (порт 80 не используется)
  python run_win.py --80     # :80 → :5000 (нужен админ!)
"""
import sys, os, subprocess, threading, time, urllib.request, socketserver, http.server

HOST = "0.0.0.0"
API_PORT = 5000
PROXY_PORT = 80

FASTAPI_CMD = [sys.executable, "-m", "uvicorn", "main:app",
               "--host", HOST, "--port", str(API_PORT)]


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    """Простой прокси :80 → :5000 для GET/POST запросов."""

    def _proxy(self):
        target = f"http://127.0.0.1:{API_PORT}{self.path}"
        try:
            data = self.rfile.read(int(self.headers.get("content-length", 0)))
            req = urllib.request.Request(target, data=data,
                                         headers=dict(self.headers),
                                         method=self.command)
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    skip = {"transfer-encoding", "content-encoding",
                            "connection", "keep-alive"}
                    if k.lower() not in skip:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")

    def do_GET(self):   self._proxy()
    def do_POST(self):  self._proxy()
    def do_PUT(self):   self._proxy()
    def do_DELETE(self): self._proxy()
    def do_HEAD(self):  self._proxy()
    def log_message(self, fmt, *a):
        pass  # не шумим


def start_fastapi():
    print(f"  FastAPI → http://{HOST}:{API_PORT}")
    sys.stdout.flush()
    proc = subprocess.Popen(FASTAPI_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline, b""):
        line = line.decode("utf-8", errors="replace").rstrip()
        if line:
            print(f"  fastapi | {line}")
    proc.wait()


def start_proxy():
    print(f"  Прокси  → http://{HOST}:{PROXY_PORT} → :{API_PORT}")
    sys.stdout.flush()
    socketserver.TCPServer.allow_reuse_address = True
    srv = http.server.HTTPServer((HOST, PROXY_PORT), ProxyHandler)
    srv.serve_forever()


if __name__ == "__main__":
    print("=" * 50)
    print("  OldMarket — Windows Launcher")
    print("=" * 50)
    print()

    use_proxy = "--80" in sys.argv
    if use_proxy:
        print("  Режим: :80 → :5000  (требуются права администратора!)")
    else:
        print("  Режим: только :5000")
        print("  Для :80 добавь флаг --80 (запусти cmd от админа)")
    print()

    # Запускаем FastAPI в фоне
    t = threading.Thread(target=start_fastapi, daemon=True)
    t.start()
    time.sleep(2)

    # Запускаем прокси если нужно
    if use_proxy:
        try:
            start_proxy()
        except PermissionError:
            print("\n  [ОШИБКА] Нет прав на порт 80. Запусти cmd от администратора.")
            print("  Или используй: python run_win.py (без --80)\n")
            sys.exit(1)
    else:
        print("\n  Нажми Ctrl+C для остановки\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  Остановлено.")
