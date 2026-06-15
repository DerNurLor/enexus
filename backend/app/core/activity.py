from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any, Optional

import structlog
from fastapi import BackgroundTasks, Request

log = structlog.get_logger(__name__)


async def _write_activity(
    action: str,
    user_id: Optional[str],
    tg_id: Optional[int],
    request_id: Optional[str],
    ip: Optional[str],
    user_agent: Optional[str],
    details: dict[str, Any],
) -> None:
    try:
        from app.auth.models import AuthActivityLog
        await AuthActivityLog(
            action=action,
            user_id=user_id,
            tg_id=tg_id,
            request_id=request_id,
            ip=ip,
            user_agent=user_agent,
            details=details,
            timestamp=datetime.utcnow(),
        ).insert()
    except Exception as exc:
        # Never let logging crash anything
        log.warning("activity_log_write_failed", action=action, error=str(exc))


async def _write_error(
    level: str,
    message: str,
    tb: Optional[str],
    user_id: Optional[str],
    request_id: Optional[str],
    path: Optional[str],
) -> None:
    try:
        from app.auth.models import AuthErrorLog
        await AuthErrorLog(
            level=level,
            message=message,
            traceback=tb,
            user_id=user_id,
            request_id=request_id,
            path=path,
        ).insert()
    except Exception as exc:
        log.warning("error_log_write_failed", error=str(exc))


def log_activity(
    action: str,
    *,
    user_id:    Optional[str]  = None,
    tg_id:      Optional[int]  = None,
    request:    Optional[Request] = None,
    background: Optional[BackgroundTasks] = None,
    details:    Optional[dict]  = None,
) -> None:
    """Fire-and-forget: deferred via BackgroundTasks if available, else asyncio.ensure_future."""
    request_id = None
    ip         = None
    user_agent = None

    if request is not None:
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        ip         = _get_ip(request)
        user_agent = request.headers.get("user-agent", "")[:200]

    log.info(
        action,
        user_id=user_id,
        tg_id=tg_id,
        request_id=request_id,
        details=details or {},
    )

    coro = _write_activity(
        action=action,
        user_id=user_id,
        tg_id=tg_id,
        request_id=request_id,
        ip=ip,
        user_agent=user_agent,
        details=details or {},
    )

    if background is not None:
        background.add_task(lambda: __import__("asyncio").ensure_future(coro))
    else:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.ensure_future(coro)


def log_bot_message(
    tg_id: int,
    text: str,
    intent: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    log_activity(
        "bot.message",
        tg_id=tg_id,
        user_id=user_id,
        details={"text_preview": text[:120], "intent": intent},
    )


def log_bot_command(
    tg_id: int,
    command: str,
    user_id: Optional[str] = None,
) -> None:
    log_activity(
        f"bot.command.{command.lstrip('/')}",
        tg_id=tg_id,
        user_id=user_id,
        details={"command": command},
    )


async def log_error_async(
    exc: Exception,
    *,
    user_id:    Optional[str]  = None,
    request:    Optional[Request] = None,
    level:      str = "ERROR",
) -> None:
    request_id = None
    path       = None
    if request is not None:
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        path       = str(request.url.path) if request.url else None

    tb = traceback.format_exc()
    log.error(str(exc), exc_info=exc, request_id=request_id, path=path)

    await _write_error(
        level=level,
        message=str(exc),
        tb=tb if tb != "NoneType: None\n" else None,
        user_id=user_id,
        request_id=request_id,
        path=path,
    )


class ActivityLoggingMiddleware:
    _SKIP = frozenset(["/health", "/metrics", "/favicon.ico"])

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        import time
        from fastapi import Request as _Request
        request = _Request(scope)
        path = request.url.path

        if path in self._SKIP:
            return await self.app(scope, receive, send)

        start    = time.monotonic()
        status_code = 500

        async def send_intercepted(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_intercepted)
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            request_id  = getattr(getattr(scope, "state", scope.get("state", {})), "request_id", None)
            if isinstance(scope.get("state"), dict):
                request_id = scope["state"].get("request_id", request_id)

            # Not stored in Mongo — stdout only
            log.info(
                "http.request",
                method=request.method,
                path=path,
                status=status_code,
                duration_ms=round(duration_ms, 1),
                request_id=request_id,
            )


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
