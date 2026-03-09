"""
miniapp/quota_service.py
Локальная копия get_quota_status — без зависимости на app.bot.
Оригинал живёт в ecampus_bot/app/bot/middlewares/anti_flood.py.
"""
from __future__ import annotations

from app.cache.redis import get_redis


def _quota_key(chat_id: int) -> str:
    return f"quota:{chat_id}"


async def _resolve_quota(chat_id: int, default_cap: int, default_ttl: int) -> tuple[int, int]:
    """Возвращает (cap, ttl_seconds) — использует per-chat DB override если задан."""
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


async def get_quota_status(user_id: int, chat_id: int, chat_type: str) -> dict:
    """
    Возвращает текущее использование квоты для пользователя/чата.
    """
    from app.core.config import settings as _cfg

    if chat_type == "private":
        quota_id    = user_id
        default_cap = _cfg.quota_private
        # Per-user cap from AuthUser.daily_requests overrides global default
        # (mirrors the logic in ecampus_bot/app/bot/middlewares/anti_flood.py)
        try:
            from app.auth.models import AuthUser as _AuthUser
            au = await _AuthUser.find_one({"tg_id": user_id})
            if au and au.daily_requests is not None and au.daily_requests > 0:
                default_cap = au.daily_requests
        except Exception:
            pass
    else:
        quota_id    = chat_id
        default_cap = _cfg.quota_group_large

    default_ttl = _cfg.quota_ttl_hours * 3600
    cap, quota_ttl = await _resolve_quota(chat_id, default_cap, default_ttl)

    key = _quota_key(quota_id)
    r   = get_redis()
    try:
        raw      = await r.mget(key)
        ttl_secs = await r.ttl(key)
        val      = raw[0] if isinstance(raw, list) else raw
        used     = int(val) if val else 0
        ttl_secs = max(int(ttl_secs), 0)
    except Exception:
        used     = 0
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
