"""
dashboard/media_service.py
Локальная копия resolve_media_url — без зависимости на app.bot.
Оригинал живёт в ecampus_bot/app/bot/media_service.py.
"""
from __future__ import annotations

import httpx
from loguru import logger

from app.cache.redis import get_redis
from app.core.config import settings

CACHE_TTL = 3600


def _redis_key(file_unique_id: str) -> str:
    return f"tg:media:{file_unique_id}"


async def resolve_media_url(file_id: str, file_unique_id: str) -> str | None:
    if not settings.get_telegram_bot_token():
        return None

    redis_key = _redis_key(file_unique_id)
    try:
        r = get_redis()
        cached = await r.get(redis_key)
        if cached:
            return cached.decode() if isinstance(cached, bytes) else cached
    except Exception as exc:
        logger.warning(f"media Redis GET failed ({file_unique_id}): {exc}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{settings.get_telegram_bot_token()}/getFile",
                params={"file_id": file_id},
            )
            data = resp.json()
    except Exception as exc:
        logger.warning(f"media getFile HTTP error file_id={file_id}: {exc}")
        return None

    if not data.get("ok"):
        logger.warning(f"media getFile failed file_id={file_id}: {data.get('description')}")
        return None

    file_path: str | None = data.get("result", {}).get("file_path")
    if not file_path:
        return None

    url = f"https://api.telegram.org/file/bot{settings.get_telegram_bot_token()}/{file_path}"

    try:
        await get_redis().setex(redis_key, CACHE_TTL, url.encode())
    except Exception as exc:
        logger.warning(f"media Redis SET failed ({file_unique_id}): {exc}")

    return url


async def resolve_media_url_from_meta(media) -> str | None:
    if media is None:
        return None
    return await resolve_media_url(
        file_id=media.file_id,
        file_unique_id=media.file_unique_id,
    )
