from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from loguru import logger
import os

from app.core.config import settings
from app.core.observability import setup_observability
from app.auth.database import connect_auth_db, close_auth_db
from app.cache.redis import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_observability(settings.log_level)
    logger.info(f"Starting NCFU Bot Service [{settings.app_env}]")
    await connect_auth_db()
    await init_redis()

    if settings.telegram_bot_token:
        from app.bot import setup_bot
        await setup_bot()
        logger.info("Bot started (webhook mode)")
    else:
        logger.error("TELEGRAM_BOT_TOKEN not set — bot disabled")

    yield

    if settings.telegram_bot_token:
        from app.bot import teardown_bot
        await teardown_bot()

    await close_redis()
    await close_auth_db()
    logger.info("Bot service shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="NCFU Bot Service",
        version="2.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    @app.post("/webhook/telegram", include_in_schema=False)
    async def telegram_webhook(request: Request) -> Response:
        import hmac, hashlib
        from aiogram import Bot
        from app.bot import get_bot, get_dp

        secret = settings.get_telegram_webhook_secret()
        if secret:
            token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if not hmac.compare_digest(token_header, secret):
                logger.warning(f"Webhook: invalid secret from {request.client.host if request.client else '?'}")
                return Response(status_code=403)

        from aiogram.types import Update
        import orjson
        body = await request.body()
        try:
            update = Update.model_validate(orjson.loads(body))
        except Exception as e:
            logger.warning(f"Webhook: failed to parse update: {e}")
            return Response(status_code=200)

        bot = get_bot()
        dp  = get_dp()
        await dp.feed_update(bot, update)
        return Response(status_code=200)

    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "env": settings.app_env, "service": "bot"}

    @app.get("/bot/diag", include_in_schema=False)
    async def bot_diag(request: Request):
        if settings.app_env != "development":
            provided = request.headers.get("X-Admin-Secret", "")
            if not settings.graphql_secret or not provided:
                from fastapi import HTTPException
                raise HTTPException(403, "Forbidden")
            import secrets as _s
            if not _s.compare_digest(settings.get_graphql_secret(), provided):
                from fastapi import HTTPException
                raise HTTPException(403, "Forbidden")
        import httpx
        out = {
            "telegram_bot_token_set": bool(settings.get_telegram_bot_token()),
            "backend_url": settings.backend_url,
        }
        if settings.telegram_bot_token:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(
                        f"https://api.telegram.org/bot{settings.get_telegram_bot_token()}/getWebhookInfo"
                    )
                    wi = r.json().get("result", {})
                    out["webhook_url"]     = wi.get("url", "")
                    out["pending_updates"] = wi.get("pending_update_count", 0)
                    out["last_error"]      = wi.get("last_error_message", "")
            except Exception as e:
                out["error"] = str(e)
        return out

    @app.exception_handler(Exception)
    async def global_error_handler(request: Request, exc: Exception) -> Response:
        logger.exception(f"Unhandled error: {exc}")
        return Response(content='{"detail":"Internal server error"}', status_code=500, media_type="application/json")

    return app


app = create_app()
