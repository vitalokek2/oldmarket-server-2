import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from routers import apps, users, system, reviews
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
}

for route, path in static_dirs.items():
    if os.path.exists(path):
        app.mount(route, StaticFiles(directory=path), name=route.strip("/"))


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


app.include_router(apps.router)
app.include_router(users.router)
app.include_router(system.router)
app.include_router(reviews.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
