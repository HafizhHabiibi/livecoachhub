import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.tiktok_router import router
from app.api.ws_router import router as ws_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title="TikTok Live API",
    version="1.0.0"
)

app.include_router(router)
app.include_router(ws_router)

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static"
)


@app.get("/")
async def index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))