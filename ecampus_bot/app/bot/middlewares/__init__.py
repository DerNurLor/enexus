"""
Aiogram middlewares:
- LoggingMiddleware:   structured log + MongoDB activity record for every message
- RateLimitMiddleware: Redis-backed per-user rate limiting (configurable via settings)
"""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from app.cache.redis import get_redis
from app.core.config import settings

log = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user  = getattr(event, "from_user", None)
        tg_id    = getattr(tg_user, "id", None)
        username = getattr(tg_user, "username", None)
        text     = ""
        is_cmd   = False

        if isinstance(event, Message):
            text   = (event.text or event.caption or "")[:200]
            is_cmd = text.startswith("/")

        log.info(
            "bot.update",
            tg_id=tg_id,
            username=username,
            text_preview=text[:80],
            is_command=is_cmd,
        )

        start  = time.monotonic()
        result = await handler(event, data)
        ms     = (time.monotonic() - start) * 1000

        log.debug("bot.handled", tg_id=tg_id, duration_ms=round(ms, 1))

        # Persist to MongoDB (fire-and-forget)
        from app.core.activity import log_activity
        action = f"bot.command.{text.split()[0].lstrip('/')}" if is_cmd else "bot.message"
        log_activity(
            action,
            tg_id=tg_id,
            details={
                "text_preview": text[:120],
                "username": username,
                "duration_ms": round(ms, 1),
            },
        )

        return result


class RateLimitMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_id = getattr(getattr(event, "from_user", None), "id", None)
        if tg_id:
            from app.core.ratelimit import check_bot_rate_limit
            allowed = await check_bot_rate_limit(tg_id)
            if not allowed:
                if isinstance(event, Message):
                    await event.answer(
                        f"⚠️ Слишком много запросов. "
                        f"Подождите {settings.rate_limit_window} секунд."
                    )
                log.warning("bot.rate_limited", tg_id=tg_id)
                from app.core.activity import log_activity
                log_activity("bot.rate_limited", tg_id=tg_id)
                return None
        return await handler(event, data)
