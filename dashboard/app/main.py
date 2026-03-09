"""
dashboard/app/main.py

Standalone Dashboard service — Admin panel + user profile pages + REST API.
Connects to the same shared MongoDB/Redis as backend and ecampus_bot.

Endpoints:
  GET  /dashboard/admin    — Admin HTML panel
  GET  /dashboard/me       — User profile HTML panel
  GET  /dashboard/api/*    — REST API (RBAC-protected)
  GET  /health             — Health check
  GET  /metrics            — Prometheus metrics
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import os

from app.core.config import settings
from app.core.observability import setup_observability
from app.auth.database import connect_auth_db, close_auth_db
from app.cache.redis import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_observability(settings.log_level)
    logger.info(f"Starting NCFU Dashboard [{settings.app_env}]")
    await connect_auth_db()
    # Also need schedule DB for some stats (lessons, groups, etc.)
    from app.db.database import connect_db, close_db
    await connect_db()
    await init_redis()
    os.makedirs(f"{settings.static_dir}/avatars", exist_ok=True)
    yield
    await close_redis()
    from app.db.database import close_db
    await close_db()
    await close_auth_db()
    logger.info("Dashboard shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="NCFU Dashboard",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
    )

    # HTTPS enforcement in production
    if settings.app_env == "production":
        from starlette.middleware.base import BaseHTTPMiddleware

        class HTTPSEnforceMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                proto = request.headers.get("X-Forwarded-Proto", "https")
                if proto == "http":
                    url = request.url.replace(scheme="https")
                    return Response(status_code=301, headers={"Location": str(url)})
                response = await call_next(request)
                response.headers["Strict-Transport-Security"] = (
                    "max-age=63072000; includeSubDomains; preload"
                )
                return response

        app.add_middleware(HTTPSEnforceMiddleware)

    # CORS
    if settings.app_env == "development":
        allowed_origins = [
            "http://localhost:3000", "http://localhost:8000", "http://localhost:8003",
            "http://127.0.0.1:3000", "http://127.0.0.1:8000", "http://127.0.0.1:8003",
        ]
    else:
        allowed_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Static files (avatars etc.)
    os.makedirs(settings.static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    # Auth router (needed for token refresh etc.)
    from app.auth.router import router as auth_router
    app.include_router(auth_router)

    # Dashboard HTML + API
    from app.dashboard.router import router as dashboard_router
    from app.dashboard.api import api as dashboard_api
    from app.dashboard.api_chats import router as chats_router
    app.include_router(dashboard_router)
    app.include_router(dashboard_api)
    app.include_router(chats_router)

    # Optional secret admin path (defence-in-depth)
    _ap = settings.admin_path.strip("/")
    if _ap:
        from fastapi import APIRouter as _AR
        _secret = _AR(prefix=f"/{_ap}")
        _secret.include_router(dashboard_router)
        _secret.include_router(dashboard_api)
        _secret.include_router(chats_router)
        app.include_router(_secret)

    @app.get("/health", tags=["ops"])
    async def health():
        return {
            "status": "ok",
            "env": settings.app_env,
            "version": "1.0.0",
            "service": "dashboard",
        }

    @app.get("/metrics", tags=["ops"])
    async def metrics():
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.exception_handler(Exception)
    async def global_error_handler(request: Request, exc: Exception) -> Response:
        from app.core.activity import log_error_async
        await log_error_async(exc, request=request)
        if settings.sentry_dsn:
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(exc)
            except Exception:
                pass
        return Response(
            content='{"detail":"Internal server error"}',
            status_code=500,
            media_type="application/json",
        )

    return app


app = create_app()
