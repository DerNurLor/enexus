"""
media_service.py
================
Resolves Telegram file_id values into public CDN download URLs.

Flow
----
1. Check Redis key  "tg:media:<file_unique_id>"
2. HIT  → return cached URL (Telegram CDN URLs are stable for ~1 h)
3. MISS → call Bot API  getFile(file_id)  →  file.file_path
        → build  https://api.telegram.org/file/bot{TOKEN}/{file_path}
        → cache in Redis for CACHE_TTL seconds
        → return URL

Security
--------
- BOT_TOKEN is NEVER sent to the frontend.  Only the final CDN URL is returned.
- The CDN URL itself contains the token in the path (unavoidable for Telegram),
  but it is only accessible to the admin dashboard behind auth.
- We use `file_unique_id` (not `file_id`) as the Redis cache key because
  file_unique_id is stable across bot instances, while file_id is bot-specific.
"""
from __future__ import annotations

import httpx
from loguru import logger

from app.cache.redis import get_redis
from app.core.config import settings

# Telegram CDN URLs are valid for roughly 1 hour.
# We cache for 3600 s as requested, which is safe.
CACHE_TTL = 3600  # seconds


def _redis_key(file_unique_id: str) -> str:
    return f"tg:media:{file_unique_id}"


async def resolve_media_url(
    file_id: str,
    file_unique_id: str,
) -> str | None:
    """
    Return a public Telegram CDN URL for the given file_id.

    Args:
        file_id:        Telegram file_id  (bot-specific, used for the API call)
        file_unique_id: Stable unique id  (used as the Redis cache key)

    Returns:
        Full https://api.telegram.org/file/... URL, or None on any error.
    """
    if not settings.telegram_bot_token:
        logger.warning("resolve_media_url: TELEGRAM_BOT_TOKEN not configured")
        return None

    redis_key = _redis_key(file_unique_id)

    # ── 1. Cache hit ──────────────────────────────────────────────────────────
    try:
        r = get_redis()
        cached = await r.get(redis_key)
        if cached:
            url = cached.decode() if isinstance(cached, bytes) else cached
            logger.debug(f"media cache HIT file_unique_id={file_unique_id}")
            return url
    except Exception as exc:
        logger.warning(f"media Redis GET failed ({file_unique_id}): {exc}")

    # ── 2. Fetch from Telegram Bot API ────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile",
                params={"file_id": file_id},
            )
            data = resp.json()
    except Exception as exc:
        logger.warning(f"media getFile HTTP error file_id={file_id}: {exc}")
        return None

    if not data.get("ok"):
        desc = data.get("description", "unknown error")
        logger.warning(f"media getFile failed file_id={file_id}: {desc}")
        return None

    file_path: str | None = data.get("result", {}).get("file_path")
    if not file_path:
        logger.warning(f"media getFile: no file_path in response file_id={file_id}")
        return None

    url = (
        f"https://api.telegram.org/file"
        f"/bot{settings.telegram_bot_token}/{file_path}"
    )

    # ── 3. Write to cache ─────────────────────────────────────────────────────
    try:
        r = get_redis()
        await r.setex(redis_key, CACHE_TTL, url.encode())
        logger.debug(f"media cache SET file_unique_id={file_unique_id} ttl={CACHE_TTL}s")
    except Exception as exc:
        logger.warning(f"media Redis SET failed ({file_unique_id}): {exc}")

    return url


async def resolve_media_url_from_meta(media) -> str | None:
    """
    Convenience wrapper that accepts a MediaMeta Pydantic object directly.
    Returns the CDN URL or None.
    """
    if media is None:
        return None
    return await resolve_media_url(
        file_id=media.file_id,
        file_unique_id=media.file_unique_id,
    )
