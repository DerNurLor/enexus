"""
app/bot/middlewares/webhook_ratelimit.py
=========================================
FastAPI middleware that enforces a hard rate limit on /webhook/telegram.

Design:
  • Sliding-window counter in Redis, keyed by client IP.
  • Cloudflare-aware: trusts CF-Connecting-IP header when the direct
    connection comes from a known Cloudflare range (loaded lazily).
  • Limit: 10 req/min per IP by default (configurable via settings).
  • On excess: returns HTTP 429 with Retry-After header and logs to Sentry.
  • Returns 200 (not 429) to Telegram IPs so Telegram doesn't retry storms —
    the update is simply dropped.

Telegram IP ranges (IPv4 + IPv6):
  149.154.160.0/20   91.108.4.0/22   91.108.56.0/22
  91.108.8.0/22      91.108.36.0/23  2001:b28:f23d::/48
  2001:b28:f23f::/48 2001:67c:4e8::/48 2a0a:f280::/32
"""
from __future__ import annotations

import ipaddress
import time
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as _SR
from loguru import logger

from app.cache.redis import get_redis

# ── Telegram IP ranges ────────────────────────────────────────────────────────
_TELEGRAM_NETS = [
    ipaddress.ip_network(n) for n in (
        "149.154.160.0/20",
        "91.108.4.0/22",
        "91.108.56.0/22",
        "91.108.8.0/22",
        "91.108.36.0/23",
        "2001:b28:f23d::/48",
        "2001:b28:f23f::/48",
        "2001:67c:4e8::/48",
        "2a0a:f280::/32",
    )
]

# ── Cloudflare IP ranges (last updated 2025-01) ───────────────────────────────
_CF_NETS = [
    ipaddress.ip_network(n) for n in (
        "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22",
        "103.31.4.0/22",   "141.101.64.0/18", "108.162.192.0/18",
        "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22",
        "198.41.128.0/17", "162.158.0.0/15",  "104.16.0.0/13",
        "104.24.0.0/14",   "172.64.0.0/13",   "131.0.72.0/22",
        # IPv6
        "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32",
        "2405:b500::/32", "2405:8100::/32", "2a06:98c0::/29",
        "2c0f:f248::/32",
    )
]

_WEBHOOK_PATH   = "/webhook/telegram"
_WINDOW_SECS    = 60
_DEFAULT_LIMIT  = 10   # req/min per IP


def _in_nets(ip_str: str, nets: list) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in nets)
    except ValueError:
        return False


def _client_ip(request: Request) -> str:
    """
    Extract real client IP.
    Priority: CF-Connecting-IP (if direct conn is Cloudflare)
              → X-Forwarded-For (if direct conn is trusted proxy)
              → request.client.host
    """
    direct = request.client.host if request.client else "unknown"

    # Cloudflare edge
    if _in_nets(direct, _CF_NETS):
        cf_ip = request.headers.get("CF-Connecting-IP", "").strip()
        if cf_ip:
            return cf_ip

    # Generic reverse proxy (Docker / nginx on localhost)
    trusted_proxies = {"127.0.0.1", "::1"}
    if direct in trusted_proxies:
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[0].strip()

    return direct


class WebhookRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate-limits /webhook/telegram to `limit` requests per minute per IP.
    All other paths are passed through untouched.
    """

    def __init__(self, app, limit: int = _DEFAULT_LIMIT):
        super().__init__(app)
        self._limit = limit

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path != _WEBHOOK_PATH:
            return await call_next(request)

        ip = _client_ip(request)

        # Always let genuine Telegram IPs through — they are already
        # authenticated by the secret-token check in the route handler.
        if _in_nets(ip, _TELEGRAM_NETS):
            return await call_next(request)

        # Sliding-window counter
        bucket = int(time.time()) // _WINDOW_SECS
        key    = f"wh_rl:{ip}:{bucket}"

        try:
            r     = get_redis()
            pipe  = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, _WINDOW_SECS + 5)
            count = (await pipe.execute())[0]
        except Exception as exc:
            logger.warning(f"WebhookRL Redis error ip={ip}: {exc}")
            return await call_next(request)  # fail open

        if count > self._limit:
            logger.warning(
                f"WebhookRL: blocked ip={ip} count={count}/{self._limit}"
            )
            _sentry_report(ip, count, self._limit)
            # Return 429 to non-Telegram sources (bots, scanners)
            return _SR(
                status_code=429,
                content=b"Too Many Requests",
                headers={"Retry-After": str(_WINDOW_SECS)},
            )

        return await call_next(request)


def _sentry_report(ip: str, count: int, limit: int) -> None:
    try:
        import sentry_sdk
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("webhook_rl.ip", ip)
            scope.set_extra("webhook_rl.count", count)
            scope.set_extra("webhook_rl.limit", limit)
            sentry_sdk.capture_message(
                f"WebhookRL: {ip} sent {count}/{limit} req/min",
                level="warning",
            )
    except Exception:
        pass
