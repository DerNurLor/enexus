"""
backend/app/main.py

Pure API service — GraphQL schedule API, REST routes, Dashboard, Scraper/Scheduler.
Bot and MiniApp have been extracted to their own services (ecampus_bot, miniapp).

Services communicate via shared MongoDB + Redis.
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
from app.scheduler.scheduler import setup_scheduler, shutdown_scheduler
from app.graphql.schema import graphql_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_observability(settings.log_level)
    logger.info(f"Starting NCFU Schedule Backend [{settings.app_env}]")
    await connect_db()
    await connect_auth_db()
    await init_redis()
    setup_scheduler()
    os.makedirs(f"{settings.static_dir}/avatars", exist_ok=True)
    yield
    shutdown_scheduler()
    await close_redis()
    await close_auth_db()
    await close_db()
    logger.info("Backend shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="NCFU Schedule Backend API",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
    )

    if settings.app_env == "production":
        from starlette.middleware.base import BaseHTTPMiddleware

        class HTTPSEnforceMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                proto = request.headers.get("X-Forwarded-Proto", "https")
                if proto == "http":
                    url = request.url.replace(scheme="https")
                    return Response(status_code=301, headers={"Location": str(url)})
                response = await call_next(request)
                response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
                return response

        app.add_middleware(HTTPSEnforceMiddleware)

    if settings.app_env == "development":
        allowed_origins = ["http://localhost:3000","http://localhost:8000","http://localhost:8001","http://localhost:8002","http://127.0.0.1:3000","http://127.0.0.1:8000","http://127.0.0.1:8001","http://127.0.0.1:8002"]
    else:
        allowed_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
        allowed_origins += ["https://web.telegram.org","https://webk.telegram.org","https://webz.telegram.org"]

    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True,
                       allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], allow_headers=["*"])

    from starlette.middleware.base import BaseHTTPMiddleware

    class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
        _EXEMPT = {"/health", "/metrics", "/favicon.ico"}

        async def dispatch(self, request: Request, call_next):
            if request.url.path in self._EXEMPT:
                return await call_next(request)
            from app.core.ratelimit import check_rate_limit, _get_ip
            from app.core.config import settings as s
            auth = request.headers.get("Authorization", "")
            rpm = s.rate_limit_anon_rpm
            if auth.startswith("Bearer "):
                try:
                    from app.auth.security import decode_access_token
                    from app.core.ratelimit import _get_user_rpm, _bucket
                    payload = decode_access_token(auth[7:])
                    uid = payload.get("sub", "")
                    roles = payload.get("roles", [])
                    rpm = await _get_user_rpm(roles)
                    bucket_key = f"rl:user:{uid}:{_bucket()}"
                except Exception:
                    from app.core.ratelimit import _get_ip, _bucket
                    bucket_key = f"rl:anon:{_get_ip(request)}:{_bucket()}"
            else:
                from app.core.ratelimit import _bucket
                bucket_key = f"rl:anon:{_get_ip(request)}:{_bucket()}"
            try:
                await check_rate_limit(bucket_key, rpm, s.rate_limit_window)
            except Exception:
                raise
            return await call_next(request)

    app.add_middleware(GlobalRateLimitMiddleware)

    os.makedirs(settings.static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    app.include_router(graphql_router, prefix="/graphql")

    from app.auth.router import router as auth_router
    app.include_router(auth_router)

    from app.api.routes import groups, institutes, overview, rooms, schedules, scrape, search, teachers
    for route in [groups, institutes, overview, rooms, schedules, scrape, search, teachers]:
        app.include_router(route.router)

    from app.dashboard.router import router as dashboard_router
    from app.dashboard.api import api as dashboard_api
    from app.dashboard.api_chats import router as chats_router
    app.include_router(dashboard_router)
    app.include_router(dashboard_api)
    app.include_router(chats_router)

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
        return {"status": "ok", "env": settings.app_env, "version": "2.0.0", "service": "backend"}

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
                import sentry_sdk; sentry_sdk.capture_exception(exc)
            except Exception:
                pass
        return Response(content='{"detail":"Internal server error"}', status_code=500, media_type="application/json")

    return app


app = create_app()
