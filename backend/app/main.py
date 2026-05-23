from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import alerts, auth, candles, market, settings as settings_api, trades, websocket
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import create_all
from app.services.price_collector import collector

FRONTEND_DIST = Path(__file__).resolve().parent / "static" / "frontend"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    create_all()
    task: asyncio.Task | None = None
    if not settings.disable_collector:
        task = asyncio.create_task(collector.run_forever())
    try:
        yield
    finally:
        await collector.stop()
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "name": settings.app_name}


app.include_router(auth.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(candles.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(websocket.router, prefix="/api")

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


@app.get("/{path:path}", include_in_schema=False)
def serve_frontend(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")
    requested = (FRONTEND_DIST / path).resolve()
    if FRONTEND_DIST.exists() and requested.is_file() and requested.is_relative_to(FRONTEND_DIST):
        return FileResponse(requested)
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    raise HTTPException(status_code=404, detail="前端页面尚未构建")
