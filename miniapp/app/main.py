"""
miniapp/app/main.py

Telegram Mini App service — serves the SPA and its REST API.
Auth via Telegram initData → JWT. Schedule data via direct DB queries.

Depends on:
  - Shared MongoDB (ncfu_schedule + ncfu_auth)
  - Shared Redis
  - TELEGRAM_BOT_TOKEN (for initData HMAC validation)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import os

from app.core.config import settings
from app.core.observability import setup_observability
from app.db.database import connect_db, close_db
from app.auth.database import connect_auth_db, close_auth_db
from app.cache.redis import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_observability(settings.log_level)
    logger.info(f"Starting NCFU MiniApp Service [{settings.app_env}]")
    await connect_db()
    await connect_auth_db()
    await init_redis()
    yield
    await close_redis()
    await close_auth_db()
    await close_db()
    logger.info("MiniApp service shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="NCFU MiniApp Service",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    if settings.app_env == "development":
        allowed_origins = ["http://localhost:3000","http://localhost:8002","http://127.0.0.1:8002","*"]
    else:
        allowed_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
        allowed_origins += ["https://web.telegram.org","https://webk.telegram.org","https://webz.telegram.org"]

    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True,
                       allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], allow_headers=["*"])

    # ── Mini App routes ───────────────────────────────────────────────────────
    from app.miniapp.router import router as miniapp_router
    app.include_router(miniapp_router)

    from app.auth.router import router as auth_router
    app.include_router(auth_router)

    # ── Static assets (React build) ───────────────────────────────────────────
    _static = os.path.join(os.path.dirname(__file__), "miniapp", "static")
    if os.path.isdir(_static):
        app.mount("/assets", StaticFiles(directory=os.path.join(_static, "assets")), name="assets")

    # ── Ops ───────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "env": settings.app_env, "service": "miniapp"}

    @app.exception_handler(Exception)
    async def global_error_handler(request: Request, exc: Exception) -> Response:
        logger.exception(f"Unhandled error: {exc}")
        return Response(content='{"detail":"Internal server error"}', status_code=500, media_type="application/json")

    return app


app = create_app()
