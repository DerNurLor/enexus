import hashlib
import orjson
from datetime import date, datetime
from typing import Any, Optional, Callable
from redis.asyncio import Redis, ConnectionPool
from loguru import logger

from app.core.config import settings

_pool: Optional[ConnectionPool] = None
_redis: Optional[Redis] = None


def _orjson_default(obj: Any) -> Any:
    # bson ObjectId — just stringify it
    if hasattr(obj, "__str__") and type(obj).__name__ == "ObjectId":
        return str(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"Type is not JSON serializable: {type(obj).__name__}")


async def init_redis() -> None:
    global _pool, _redis
    _pool = ConnectionPool.from_url(settings.redis_url, decode_responses=False, max_connections=20)
    _redis = Redis(connection_pool=_pool)
    await _redis.ping()
    logger.info("Redis ready.")


async def close_redis() -> None:
    global _redis, _pool
    if _redis:
        await _redis.aclose()
    if _pool:
        await _pool.aclose()


def get_redis() -> Redis:
    assert _redis is not None
    return _redis


def cache_key(*parts) -> str:
    return ":".join(str(p) for p in parts)


def hash_params(**kwargs) -> str:
    raw = orjson.dumps(kwargs, option=orjson.OPT_SORT_KEYS)
    return hashlib.md5(raw).hexdigest()[:12]


async def cached(key: str, ttl: int, fn: Callable) -> Any:
    r = get_redis()
    try:
        hit = await r.get(key)
        if hit is not None:
            return orjson.loads(hit)
    except Exception as exc:
        logger.warning(f"Redis GET failed ({key}): {exc}")
    result = await fn()
    try:
        await r.setex(
            key, ttl,
            orjson.dumps(result, option=orjson.OPT_NON_STR_KEYS, default=_orjson_default),
        )
    except Exception as exc:
        logger.warning(f"Redis SET failed ({key}): {exc}")
    return result


async def invalidate_pattern(pattern: str) -> int:
    r = get_redis()
    deleted = 0
    async for key in r.scan_iter(pattern):
        await r.delete(key)
        deleted += 1
    return deleted

