"""
Redis-backed conversation memory for the Telegram bot.
Stores the last MAX_HISTORY messages per user as JSON in Redis.
Key: conv:{tg_id}  TTL: 24 h
"""
from __future__ import annotations
import json
from datetime import datetime
from loguru import logger

MAX_HISTORY = 15
REDIS_TTL   = 86400   # 24 h


def _key(tg_id: int) -> str:
    return f"conv:{tg_id}"


async def get_history(tg_id: int) -> list[dict]:
    try:
        from app.cache.redis import get_redis
        raw = await get_redis().get(_key(tg_id))
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(f"conv.get failed tg_id={tg_id}: {exc}")
    return []


async def add_message(tg_id: int, role: str, content: str,
                      message_id: int | None = None,
                      media_type: str | None = None,
                      media_file_id: str | None = None) -> None:
    """Add message to Redis (short-term) and persist to MongoDB (long-term)."""
    msg = {
        "role": role, "content": content,
        "ts": datetime.utcnow().isoformat(),
    }
    if message_id:    msg["message_id"]    = message_id
    if media_type:    msg["media_type"]    = media_type
    if media_file_id: msg["media_file_id"] = media_file_id

    # ── Redis (short-term context for AI) ────────────────────────────────────
    try:
        from app.cache.redis import get_redis
        r       = get_redis()
        history = await get_history(tg_id)
        history.append(msg)
        history = history[-MAX_HISTORY:]
        await r.setex(_key(tg_id), REDIS_TTL,
                      json.dumps(history, ensure_ascii=False))
    except Exception as exc:
        logger.warning(f"conv.redis.add failed tg_id={tg_id}: {exc}")

    # ── MongoDB (full persistent history) ────────────────────────────────────
    try:
        from app.auth.models import BotConversation
        conv = await BotConversation.find_one(BotConversation.tg_id == tg_id)
        if conv is None:
            conv = BotConversation(tg_id=tg_id, messages=[msg])
            await conv.insert()
        else:
            conv.messages.append(msg)
            # Keep last 500 messages in MongoDB
            if len(conv.messages) > 500:
                conv.messages = conv.messages[-500:]
            conv.updated_at = datetime.utcnow()
            await conv.save()
    except Exception as exc:
        logger.warning(f"conv.mongo.add failed tg_id={tg_id}: {exc}")


async def clear_history(tg_id: int) -> None:
    try:
        from app.cache.redis import get_redis
        await get_redis().delete(_key(tg_id))
    except Exception as exc:
        logger.warning(f"conv.clear failed tg_id={tg_id}: {exc}")


async def get_history_for_admin(tg_id: int, offset: int = 0, limit: int = 30) -> tuple[list[dict], int]:
    """Return paginated history from MongoDB for dashboard chat viewer.
    Returns (messages, total_count) newest-first."""
    try:
        from app.auth.models import BotConversation
        conv = await BotConversation.find_one(BotConversation.tg_id == tg_id)
        if conv and conv.messages:
            msgs = conv.messages
            total = len(msgs)
            # Newest first, paginated
            sliced = list(reversed(msgs))[offset: offset + limit]
            return sliced, total
    except Exception as exc:
        logger.warning(f"conv.admin.get failed tg_id={tg_id}: {exc}")
    # Fallback to Redis
    history = await get_history(tg_id)
    total = len(history)
    sliced = list(reversed(history))[offset: offset + limit]
    return sliced, total


def build_context_prompt(history: list[dict]) -> str:
    """Build a short context block to prepend to the LLM system prompt."""
    if not history:
        return ""
    recent = history[-8:]
    lines = []
    for m in recent:
        role = "Пользователь" if m["role"] == "user" else "Бот"
        lines.append(f"{role}: {m['content'][:180]}")
    return "Контекст диалога:\n" + "\n".join(lines)
