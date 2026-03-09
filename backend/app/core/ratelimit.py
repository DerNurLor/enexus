"""
Redis-based rate limiting — HARDENED.

Security changes:
  [S1] X-Forwarded-For validation — only trust from known proxies
  [S2] Graceful Redis failure handling
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import Depends, HTTPException, Request, status
from loguru import logger

from app.cache.redis import get_redis
from app.core.config import settings

RateLimitKind = Literal["user", "anon", "bot"]

# ── Role-based RPM override cache (refreshed every 60 s) ─────────────────────
import time as _time
_rpm_cache: dict[str, Optional[int]] = {}
_rpm_cache_ts: float = 0.0


async def _get_role_rpm(role_name: str) -> Optional[int]:
    global _rpm_cache, _rpm_cache_ts
    now = _time.monotonic()
    if now - _rpm_cache_ts > 60:
        try:
            from app.auth.models import AuthRole
            roles = await AuthRole.find_all().to_list()
            _rpm_cache = {}
            for r in roles:
                override = getattr(r, "rate_limit_rpm", None)
                _rpm_cache[r.name] = override
        except Exception as exc:
            logger.warning(f"RPM cache refresh failed: {exc}")
        _rpm_cache_ts = now
    return _rpm_cache.get(role_name)


async def _get_user_rpm(roles: list[str]) -> int:
    best = settings.rate_limit_user_rpm
    for role in roles:
        override = await _get_role_rpm(role)
        if override is not None and override > best:
            best = override
    return best


# ── Core check ───────────────────────────────────────────────────────────────

async def check_rate_limit(
    redis_key: str,
    rpm: int,
    window: int = 60,
) -> None:
    r = get_redis()
    try:
        count = await r.incr(redis_key)
        if count == 1:
            await r.expire(redis_key, window)
        if count > rpm:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {rpm} requests per {window}s.",
                headers={"Retry-After": str(window)},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # [S2] Never let Redis errors block requests
        logger.warning(f"Rate limit check failed (key={redis_key}): {exc}")


# ── FastAPI dependency factories ──────────────────────────────────────────────

def rate_limit_user():
    async def dep(request: Request) -> None:
        user = getattr(request.state, "current_user", None)
        if user is None:
            return
        rpm = await _get_user_rpm(getattr(user, "roles", []))
        key = f"rl:user:{user.id}:{_bucket()}"
        await check_rate_limit(key, rpm, settings.rate_limit_window)
    return dep


def rate_limit_anon():
    async def dep(request: Request) -> None:
        ip = _get_ip(request)
        key = f"rl:anon:{ip}:{_bucket()}"
        await check_rate_limit(key, settings.rate_limit_anon_rpm, settings.rate_limit_window)
    return dep


# ── Bot rate limiting ──────────────────────────────────────────────────────────

async def check_bot_rate_limit(tg_id: int) -> bool:
    r = get_redis()
    key = f"rl:bot:{tg_id}:{_bucket()}"
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, settings.rate_limit_window)
        return count <= settings.rate_limit_bot_rpm
    except Exception as exc:
        logger.warning(f"Bot rate limit check failed: {exc}")
        return True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bucket() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")


# [S1] Trusted proxy IPs for X-Forwarded-For
_TRUSTED_PROXIES = {
    "127.0.0.1", "::1",
    # Docker default bridge network
    "172.16.0.0/12", "10.0.0.0/8", "192.168.0.0/16",
}


def _is_trusted_proxy(ip: str) -> bool:
    """Check if IP is a known proxy/container IP."""
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip)
        for proxy in _TRUSTED_PROXIES:
            if "/" in proxy:
                if addr in ipaddress.ip_network(proxy, strict=False):
                    return True
            else:
                if addr == ipaddress.ip_address(proxy):
                    return True
    except ValueError:
        pass
    return False


def _get_ip(request: Request) -> str:
    """
    [S1] Extract client IP with proxy trust validation.
    Only trusts X-Forwarded-For from known proxy IPs.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Only trust XFF if the direct connection is from a known proxy
    if _is_trusted_proxy(client_ip):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the leftmost (client) IP
            return forwarded.split(",")[0].strip()

    return client_ip


# ── Flush the RPM cache ──────────────────────────────────────────────────────

def flush_rpm_cache() -> None:
    global _rpm_cache_ts
    _rpm_cache_ts = 0.0
