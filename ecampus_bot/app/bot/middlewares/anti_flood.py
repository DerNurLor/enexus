"""
app/bot/middlewares/anti_flood.py
==================================
Two aiogram middlewares:

1. AntiFloodMiddleware
   Per-user flood control (5 msg/min by default, 2× for Premium).
   Callback queries are NOT counted — button presses must always work.
   Silent drop on violation (no reply to spammer).
   Violations reported to Sentry.

2. MessageLimitMiddleware
   Hard AI-query cap per chat, 7-hour rolling TTL.

   Private chats : 3 queries per user_id
   Group chats   : 3 (small) or 5 (≥4 members) per chat_id

   Exempt commands (/start /help /miniapp /mykey /roles /support /suggest)
   never count against the cap.

NOTE: All settings are read lazily inside __call__ (not at module import time)
      so that pydantic-settings has already loaded the .env file.
"""
from __future__ import annotations

import time
from contextvars import ContextVar
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from loguru import logger

from app.cache.redis import get_redis

# Set to True from handler when bot-side error occurred — middleware will decrement quota
quota_error_flag: ContextVar[bool] = ContextVar("quota_error_flag", default=False)

# Commands that are always free (never consume quota)
_EXEMPT_COMMANDS = frozenset({
    "/start", "/help", "/miniapp", "/mykey",
    "/roles", "/support", "/suggest", "/about", "/limit",
    "/login", "/code",   # авторизация через код — не AI-запрос
})

def _make_limit_msg(chat_type: str, miniapp_url: str) -> tuple[str, object]:
    """Return (text, reply_markup) for the limit-exceeded message."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    if chat_type in ('group', 'supergroup'):
        text = (
            "⏳ <b>Лимит запросов этого чата исчерпан.</b>\n\n"
            "Бот ограничивает количество AI-запросов на группу, чтобы обеспечить "
            "доступ для всех. Лимит сбрасывается автоматически.\n\n"
            "📅 Пока можно воспользоваться расписанием напрямую:"
        )
    else:
        text = (
            "⏳ <b>Лимит ваших запросов исчерпан.</b>\n\n"
            "Лимит сбрасывается каждые 7 часов.\n\n"
            "📅 Пока можно воспользоваться расписанием напрямую:"
        )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📅 Открыть расписание",
            web_app=WebAppInfo(url=miniapp_url),
        )
    ]])
    return text, kb


# ── Helpers ───────────────────────────────────────────────────────────────────

def _flood_key(user_id: int, bucket: int) -> str:
    return f"flood:{user_id}:{bucket}"


def _quota_key(chat_id: int) -> str:
    return f"quota:{chat_id}"


def _is_exempt(message: Message) -> bool:
    text = (message.text or "").strip().lower()
    if not text.startswith("/"):
        return False
    cmd = text.split()[0].split("@")[0]   # strip @botname suffix
    return cmd in _EXEMPT_COMMANDS


def _is_premium(message: Message) -> bool:
    user = message.from_user
    return bool(user and getattr(user, "is_premium", False))


# ── Middleware 1: Anti-Flood ──────────────────────────────────────────────────

class AntiFloodMiddleware(BaseMiddleware):
    """
    Drops updates from users who exceed flood_max_messages per flood_window_secs.
    Settings are read lazily on first call to avoid import-time AttributeError.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user = event.from_user
        if not user:
            return await handler(event, data)

        # Lazy settings read — safe after app startup
        from app.core.config import settings
        flood_window = settings.flood_window_secs
        flood_max    = settings.flood_max_messages
        limit        = flood_max * 2 if _is_premium(event) else flood_max

        bucket = int(time.time()) // flood_window
        key    = _flood_key(user.id, bucket)

        try:
            r    = get_redis()
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, flood_window + 5)
            count = (await pipe.execute())[0]
        except Exception as exc:
            logger.warning(f"AntiFlood Redis error uid={user.id}: {exc}")
            return await handler(event, data)   # fail open

        if count > limit:
            logger.warning(
                f"AntiFlood: dropped uid={user.id} username={user.username!r} "
                f"count={count}/{limit}"
            )
            _report_suspicious(user.id, user.username, count, limit)
            return None   # silently drop

        return await handler(event, data)


# ── Middleware 2: Message Quota ───────────────────────────────────────────────

class MessageLimitMiddleware(BaseMiddleware):
    """
    Enforces per-chat AI query quotas with a rolling TTL.

    Priority for cap / TTL:
      1. ChatSettings.bot_quota_cap / bot_quota_ttl_hours  (per-chat DB override)
      2. Global config settings                            (fallback)

    Private chats: keyed by user_id
    Group chats:   keyed by chat_id
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        if _is_exempt(event):
            return await handler(event, data)

        chat = event.chat
        user = event.from_user
        if not chat or not user:
            return await handler(event, data)

        from app.core.config import settings as _cfg
        chat_type = chat.type   # "private" | "group" | "supergroup" | "channel"

        # Resolve quota_id and default cap/ttl
        if chat_type == "private":
            quota_id    = user.id
            default_cap = _cfg.quota_private
            # Per-user cap from AuthUser.daily_requests overrides global default
            try:
                from app.auth.models import AuthUser as _AuthUser
                au = await _AuthUser.find_one({"tg_id": user.id})
                if au and au.daily_requests is not None and au.daily_requests > 0:
                    default_cap = au.daily_requests
            except Exception:
                pass
        else:
            quota_id    = chat.id
            default_cap = await _group_cap(event, _cfg.quota_group_small, _cfg.quota_group_large)

        default_ttl = _cfg.quota_ttl_hours * 3600

        # Per-chat DB override (async, cached by beanie)
        cap, quota_ttl = await _resolve_quota(chat.id, default_cap, default_ttl)

        key = _quota_key(quota_id)
        r   = get_redis()

        try:
            # Check BEFORE incrementing — don't count blocked requests
            raw = await r.get(key)
            current = int(raw) if raw else 0

            if current >= cap:
                logger.info(
                    f"MessageLimit: chat={chat.id} type={chat_type} "
                    f"count={current}/{cap} uid={user.id} (blocked before increment)"
                )
                try:
                    from app.core.config import settings as _s
                    miniapp_url = f"{_s.webhook_base_url}/miniapp"
                    limit_text, limit_kb = _make_limit_msg(str(chat_type), miniapp_url)
                    await event.answer(limit_text, parse_mode="HTML", reply_markup=limit_kb)
                except Exception:
                    pass
                return None

            # Increment only if allowed
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            results    = await pipe.execute()
            count, ttl = results[0], results[1]

            if count == 1 or ttl < 0:
                await r.expire(key, quota_ttl)
        except Exception as exc:
            logger.warning(f"MessageLimit Redis error chat={chat.id}: {exc}")
            return await handler(event, data)   # fail open

        # Reset flag for this request
        quota_error_flag.set(False)

        # Call handler — if it raises/returns error, decrement quota back
        try:
            result = await handler(event, data)
            # Handler can signal error via quota_error_flag ContextVar
            if quota_error_flag.get():
                try:
                    await r.decr(key)
                except Exception:
                    pass
            return result
        except Exception as handler_exc:
            try:
                await r.decr(key)
            except Exception:
                pass
            raise handler_exc


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _resolve_quota(chat_id: int, default_cap: int, default_ttl: int) -> tuple[int, int]:
    """Return (cap, ttl_seconds) — uses per-chat DB override if set."""
    try:
        from app.models.chat_settings import ChatSettings
        cs = await ChatSettings.find_one(ChatSettings.chat_id == chat_id)
        if cs:
            cap = cs.bot_quota_cap if cs.bot_quota_cap is not None else default_cap
            ttl = (cs.bot_quota_ttl_hours * 3600) if cs.bot_quota_ttl_hours is not None else default_ttl
            return cap, ttl
    except Exception:
        pass
    return default_cap, default_ttl


async def _group_cap(message: Message, small: int, large: int) -> int:
    try:
        count = await message.bot.get_chat_member_count(message.chat.id)
        return large if count >= 4 else small
    except Exception:
        return small


def _report_suspicious(
    user_id: int,
    username: str | None,
    count: int,
    limit: int,
) -> None:
    try:
        import sentry_sdk
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("flood.user_id", user_id)
            scope.set_tag("flood.username", username or "unknown")
            scope.set_extra("flood.count", count)
            scope.set_extra("flood.limit", limit)
            sentry_sdk.capture_message(
                f"AntiFlood: user {user_id} sent {count}/{limit} msgs",
                level="warning",
            )
    except Exception:
        pass


# ── Public API — used by /limit command and miniapp profile ───────────────────

async def get_quota_status(user_id: int, chat_id: int, chat_type: str) -> dict:
    """
    Return current quota usage for a user/chat.
    """
    from app.core.config import settings as _cfg

    if chat_type == "private":
        quota_id    = user_id
        default_cap = _cfg.quota_private
        # Per-user cap from AuthUser.daily_requests overrides global default
        try:
            from app.auth.models import AuthUser as _AuthUser
            au = await _AuthUser.find_one({"tg_id": user_id})
            if au and au.daily_requests is not None and au.daily_requests > 0:
                default_cap = au.daily_requests
        except Exception:
            pass
    else:
        quota_id    = chat_id
        default_cap = _cfg.quota_group_large  # conservative estimate

    default_ttl = _cfg.quota_ttl_hours * 3600
    cap, quota_ttl = await _resolve_quota(chat_id, default_cap, default_ttl)

    key = _quota_key(quota_id)
    r   = get_redis()
    try:
        raw, ttl_secs = await r.mget(key), await r.ttl(key)
        # mget returns a list
        val = raw[0] if isinstance(raw, list) else raw
        used     = int(val) if val else 0
        ttl_secs = max(int(ttl_secs), 0)
    except Exception:
        used = 0
        ttl_secs = quota_ttl

    remaining = max(cap - used, 0)
    return {
        "used":      used,
        "cap":       cap,
        "ttl_hours": quota_ttl // 3600,
        "ttl_secs":  ttl_secs,
        "remaining": remaining,
        "exhausted": used >= cap,
    }


async def reset_user_quota(tg_id: int) -> bool:
    """Reset quota counter for a private user by tg_id. Returns True on success."""
    key = _quota_key(tg_id)
    r = get_redis()
    try:
        await r.delete(key)
        return True
    except Exception as exc:
        logger.warning(f"reset_user_quota failed tg_id={tg_id}: {exc}")
        return False
