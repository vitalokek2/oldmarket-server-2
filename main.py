import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from routers import apps, users, system, reviews, submissions
from security import ensure_security_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_security_tables()
    yield

app = FastAPI(title="AltMart API", lifespan=lifespan)

# --- СТАТИКА ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dirs = {
    "/html/apps": os.path.join(BASE_DIR, "downloaded", "html", "apps"),
    "/html/screenshots": os.path.join(BASE_DIR, "downloaded", "html", "screenshots"),
    "/html/avatars": os.path.join(BASE_DIR, "downloaded", "html", "avatars"),
    "/apks": os.path.join(BASE_DIR, "downloaded", "apks"),
    "/submissions": os.path.join(BASE_DIR, "downloaded", "submissions"),
    "/site": os.path.join(BASE_DIR, "site"),
}

for route, path in static_dirs.items():
    if os.path.exists(path):
        app.mount(route, StaticFiles(directory=path), name=route.strip("/"))

def _serve_html(name: str):
    path = os.path.join(BASE_DIR, "site", name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=f.read())
    return {"message": f"{name} not found"}


@app.get("/", include_in_schema=False)
async def root():
    return _serve_html("index.html")

@app.get("/login.html", include_in_schema=False)
async def login_page():
    return _serve_html("login.html")

@app.get("/register.html", include_in_schema=False)
async def register_page():
    return _serve_html("login.html")

@app.get("/profile.html", include_in_schema=False)
async def profile_page():
    return _serve_html("profile.html")

@app.get("/submit.html", include_in_schema=False)
async def submit_page():
    return _serve_html("submit.html")

@app.get("/app.html", include_in_schema=False)
async def app_page():
    return _serve_html("app.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

app.include_router(apps.router)
app.include_router(users.router)
app.include_router(system.router)
app.include_router(reviews.router)
app.include_router(submissions.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
