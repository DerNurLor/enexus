from __future__ import annotations

import re
import sys
import logging
from typing import Any

import structlog
from loguru import logger

from app.core.config import settings


_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "token", "secret", "password", "passwd", "api_key", "apikey",
    "authorization", "auth", "jwt", "access_token", "refresh_token",
    "dsn", "sentry_dsn", "private_key", "client_secret", "webhook_secret",
    "x-admin-secret", "x-telegram-bot-api-secret-token",
    "openai_api_key", "mongo_uri", "redis_url",
})

_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r"\d{9,10}:AA[0-9A-Za-z_-]{33}"),          # Telegram bot token
    re.compile(r"sk-[A-Za-z0-9]{32,}"),                    # OpenAI key
    re.compile(r"[A-Za-z0-9]{64,}"),                       # Long hex/b64 secrets
    re.compile(r"https://[^@]+@[^/]+\.ingest\.[^/]+/\d+"), # Sentry DSN
    re.compile(r"mongodb://[^@\s]+:[^@\s]+@"),             # Mongo URI with creds
    re.compile(r"redis://:[^@\s]+@"),                      # Redis URL with password
]

_REDACTED = "**REDACTED**"


def _scrub_value(v: Any) -> Any:
    if isinstance(v, str):
        for pattern in _SECRET_PATTERNS:
            if pattern.search(v):
                return _REDACTED
    if isinstance(v, dict):
        return {k: _REDACTED if k.lower() in _SENSITIVE_KEYS else _scrub_value(val)
                for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return type(v)(_scrub_value(item) for item in v)
    return v


def _sensitive_data_scrubber(
    logger_: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Sanitises every key/value before any sink receives it."""
    return {k: _REDACTED if k.lower() in _SENSITIVE_KEYS else _scrub_value(v)
            for k, v in event_dict.items()}


def _add_app_context(
    logger_: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    event_dict["env"]     = settings.app_env
    event_dict["version"] = "2.0.0"
    return event_dict


def _setup_structlog(level: str) -> None:
    is_dev = settings.app_env in ("development", "dev", "local")

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _add_app_context,
        _sensitive_data_scrubber,  # always last before renderer
    ]

    if is_dev:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def _setup_loguru(level: str) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - {message}"
        ),
        enqueue=True,  # thread-safe async logging
    )


def _setup_sentry() -> None:
    dsn = settings.get_sentry_dsn()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.pymongo import PyMongoIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.loguru import LoguruIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.sentry_env or settings.app_env,
            traces_sample_rate=settings.sentry_traces_rate,
            profiles_sample_rate=0.0,
            integrations=[
                StarletteIntegration(transaction_style="url"),
                FastApiIntegration(transaction_style="url"),
                PyMongoIntegration(),
                RedisIntegration(),
                LoguruIntegration(),
            ],
            before_send=_sentry_filter,
            send_default_pii=False,
        )
        logger.info("Sentry initialised [environment={}]", settings.app_env)
    except ImportError:
        logger.warning("sentry-sdk not installed — Sentry disabled")
    except Exception as exc:
        logger.warning(f"Sentry init failed: {exc}")


def _sentry_filter(event: dict, hint: dict) -> dict | None:
    request = event.get("request", {})
    url = request.get("url", "")
    if url.endswith("/health") or url.endswith("/metrics"):
        return None
    exceptions = event.get("exception", {}).get("values", [])
    for exc_val in exceptions:
        if exc_val.get("type") == "HTTPException" and event.get("level") != "fatal":
            return None
    return event


def setup_observability(level: str = "INFO") -> None:
    """Idempotent — call once at startup."""
    _setup_sentry()
    _setup_loguru(level)
    _setup_structlog(level)
    logger.info(
        "Observability ready [level={}, sentry={}]",
        level,
        "on" if settings.get_sentry_dsn() else "off",
    )
