"""
dashboard/conversations.py
==========================
Dashboard REST API for the conversation history viewer.

Endpoints
---------
GET  /dashboard/chats                       — list all users who have messages
GET  /dashboard/chats/{tg_id}               — paginated messages, newest-first
GET  /dashboard/chats/{tg_id}/media         — media-only filter
POST /dashboard/chats/{tg_id}/send          — send a message from admin

Design choices
--------------
- BOT_TOKEN is never returned to the frontend.  media_url is resolved
  server-side and only the final CDN URL is sent.
- Redis caches CDN URLs for 3600 s (see media_service.py).
- Pagination: `before_id` cursor (MongoDB _id / message_id) for efficient
  "load more" without skipping pages on concurrent inserts.
- Media URLs are resolved concurrently (asyncio.gather) to keep latency low.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

from app.auth.dependencies import require_permission
from app.auth.models import AuthUser
from app.auth.avatars import get_avatar_url
from app.models.conversation import Conversation, MediaMeta
from app.dashboard.media_service import resolve_media_url

conversations_router = APIRouter(
    prefix="/dashboard/chats",
    tags=["dashboard-conversations"],
)


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _fmt_media(media: MediaMeta | None) -> dict | None:
    """Serialise MediaMeta to a plain dict (without media_url — added later)."""
    if media is None:
        return None
    return {
        "kind":              media.kind,
        "file_id":           media.file_id,
        "file_unique_id":    media.file_unique_id,
        "file_size":         media.file_size,
        "mime_type":         media.mime_type,
        "width":             media.width,
        "height":            media.height,
        "duration":          media.duration,
        "file_name":         media.file_name,
        "title":             media.title,
        "performer":         media.performer,
        "sticker_emoji":     media.sticker_emoji,
        "sticker_type":      media.sticker_type,
        "sticker_set_name":  media.sticker_set_name,
        "thumbnail_file_id": media.thumbnail_file_id,
        # media_url is injected asynchronously after this dict is built
        "media_url":         None,
    }


def _fmt_message(msg: Conversation) -> dict:
    """Convert a Conversation document to a dashboard-safe dict."""
    ts = msg.timestamp
    return {
        "id":                  str(msg.id),
        "tg_id":               msg.tg_id,
        "message_id":          msg.message_id,
        "role":                msg.role,
        "timestamp":           ts.isoformat() if ts else "",
        "text":                msg.text,
        "html_text":           msg.html_text or msg.text,
        "entities":            msg.entities,
        # forward
        "is_forward":          msg.forward is not None,
        "forward_name":        msg.forward.name    if msg.forward else None,
        "forward_tg_id":       msg.forward.tg_id   if msg.forward else None,
        "forward_kind":        msg.forward.kind     if msg.forward else None,
        "forward_date":        msg.forward.date.isoformat() if (msg.forward and msg.forward.date) else None,
        # reply-to
        "reply_to_message_id": msg.reply_to_message_id,
        "reply_to_text":       msg.reply_to_text,
        # media block (media_url added in caller)
        "media":               _fmt_media(msg.media),
    }


async def _inject_media_urls(messages: list[dict]) -> None:
    """
    Resolve media CDN URLs for all messages that have media, in parallel.
    Mutates the dicts in-place (sets media["media_url"]).
    BOT_TOKEN never leaves this function.
    """
    tasks = []
    targets: list[dict] = []  # the media sub-dicts that need a url

    for msg in messages:
        media_dict = msg.get("media")
        if not media_dict:
            continue
        file_id        = media_dict.get("file_id")
        file_unique_id = media_dict.get("file_unique_id")
        if not file_id or not file_unique_id:
            continue
        tasks.append(resolve_media_url(file_id, file_unique_id))
        targets.append(media_dict)

    if not tasks:
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for media_dict, result in zip(targets, results):
        if isinstance(result, Exception):
            logger.warning(f"media URL resolution failed: {result}")
            media_dict["media_url"] = None
        else:
            media_dict["media_url"] = result


# ── Endpoints ─────────────────────────────────────────────────────────────────

@conversations_router.get("")
async def list_chats(
    q:     Optional[str] = None,
    skip:  int = 0,
    limit: int = Query(default=50, le=200),
    _: AuthUser = Depends(require_permission("admin:full")),
):
    """
    Return all users who have conversation messages, sorted by most-recent
    message.  Joins with auth_users for display metadata.
    """
    from app.auth.database import get_auth_db

    db  = get_auth_db()
    col = db.get_collection("conversations")

    pipeline = [
        {"$sort": {"timestamp": -1}},
        {
            "$group": {
                "_id":        "$tg_id",
                "last_ts":    {"$first": "$timestamp"},
                "last_text":  {"$first": "$text"},
                "last_role":  {"$first": "$role"},
                "msg_count":  {"$sum": 1},
            }
        },
        {"$sort": {"last_ts": -1}},
        {"$skip": skip},
        {"$limit": limit},
    ]
    rows = await col.aggregate(pipeline).to_list(limit)

    tg_ids    = [r["_id"] for r in rows]
    users_col = db.get_collection("auth_users")
    user_docs = await users_col.find({"tg_id": {"$in": tg_ids}}).to_list(limit)
    user_map  = {u["tg_id"]: u for u in user_docs}

    # Optional text search filter
    if q and q.strip():
        q_lower = q.strip().lower()
        rows = [
            r for r in rows
            if (
                q_lower in (user_map.get(r["_id"], {}).get("username") or "").lower()
                or q_lower in (user_map.get(r["_id"], {}).get("first_name") or "").lower()
                or q_lower in str(r["_id"])
            )
        ]

    result = []
    for r in rows:
        tid = r["_id"]
        u   = user_map.get(tid, {})
        fn  = u.get("first_name", "")
        ln  = u.get("last_name", "")
        display = f"{fn} {ln}".strip() or f"tg:{tid}"
        ts      = r.get("last_ts")
        result.append({
            "tg_id":      tid,
            "display":    display,
            "username":   u.get("username"),
            "avatar":     get_avatar_url(tid),
            "last_text":  (r.get("last_text") or "")[:80],
            "last_role":  r.get("last_role", "user"),
            "last_ts":    ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
            "msg_count":  r.get("msg_count", 0),
            "is_blocked": u.get("is_blocked", False),
        })

    return {"chats": result, "total": len(result)}


@conversations_router.get("/{tg_id}")
async def get_chat_history(
    tg_id:      int,
    offset:     int           = 0,
    limit:      int           = Query(default=30, le=100),
    media_kind: Optional[str] = None,   # photo|video|animation|sticker|voice|video_note|audio|document
    date_from:  Optional[str] = None,   # YYYY-MM-DD
    date_to:    Optional[str] = None,   # YYYY-MM-DD
    _: AuthUser = Depends(require_permission("admin:full")),
):
    """
    Return paginated conversation history for one user, newest-first.
    media_url is resolved server-side and included in each media block.
    BOT_TOKEN is never exposed.
    """
    from beanie.operators import GTE, LTE

    query: dict = {"tg_id": tg_id}

    if media_kind:
        if media_kind == "link":
            # Special pseudo-filter: messages containing URLs
            query["$or"] = [
                {"text":      {"$regex": r"https?://", "$options": "i"}},
                {"html_text": {"$regex": r"https?://", "$options": "i"}},
            ]
        else:
            query["media.kind"] = media_kind

    # Date range
    date_filter: dict = {}
    if date_from:
        try:
            date_filter["$gte"] = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            end = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59)
            date_filter["$lte"] = end
        except ValueError:
            pass
    if date_filter:
        query["timestamp"] = date_filter

    # Use Motor directly for the raw query (Beanie ODM for simple lookups,
    # Motor for paginated aggregates to avoid double-deserialisation overhead)
    from app.auth.database import get_auth_db
    col = get_auth_db().get_collection("conversations")

    total = await col.count_documents(query)
    raw   = (
        await col.find(query)
        .sort("timestamp", -1)
        .skip(offset)
        .limit(limit)
        .to_list(limit)
    )

    # Deserialise via Beanie model for type safety, then serialise to dict
    msgs_dicts: list[dict] = []
    for doc in raw:
        try:
            conv = Conversation.model_validate(doc)
            msgs_dicts.append(_fmt_message(conv))
        except Exception as exc:
            logger.warning(f"Conversation deserialise error: {exc}")

    # Resolve all media URLs in parallel (Redis-cached, BOT_TOKEN server-side only)
    await _inject_media_urls(msgs_dicts)

    # Return oldest-first for natural chat display
    msgs_dicts.reverse()

    return {
        "messages": msgs_dicts,
        "total":    total,
        "tg_id":    tg_id,
        "offset":   offset,
        "limit":    limit,
    }


@conversations_router.get("/{tg_id}/media")
async def get_chat_media(
    tg_id: int,
    kind:  Optional[str] = None,
    skip:  int = 0,
    limit: int = Query(default=20, le=50),
    _: AuthUser = Depends(require_permission("admin:full")),
):
    """
    Return only messages with media attachments for a user.
    Useful for building a media gallery view in the dashboard.
    """
    query: dict = {"tg_id": tg_id, "media": {"$ne": None}}
    if kind:
        query["media.kind"] = kind

    from app.auth.database import get_auth_db
    col = get_auth_db().get_collection("conversations")

    total = await col.count_documents(query)
    raw   = await col.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

    msgs_dicts: list[dict] = []
    for doc in raw:
        try:
            conv = Conversation.model_validate(doc)
            msgs_dicts.append(_fmt_message(conv))
        except Exception as exc:
            logger.warning(f"Conversation media deserialise error: {exc}")

    await _inject_media_urls(msgs_dicts)

    return {"media": msgs_dicts, "total": total, "tg_id": tg_id}


@conversations_router.get("/{tg_id}/poll")
async def poll_new_messages(
    tg_id:    int,
    after_ts: Optional[str] = None,
    _: AuthUser = Depends(require_permission("admin:full")),
):
    """
    Long-poll endpoint: returns messages newer than `after_ts`.
    Frontend calls this every ~2 s to get live updates.
    """
    query: dict = {"tg_id": tg_id}
    if after_ts:
        try:
            dt = datetime.fromisoformat(after_ts.replace("Z", "+00:00"))
            query["timestamp"] = {"$gt": dt}
        except Exception:
            pass

    from app.auth.database import get_auth_db
    col = get_auth_db().get_collection("conversations")

    raw = await col.find(query).sort("timestamp", 1).limit(50).to_list(50)

    msgs_dicts: list[dict] = []
    for doc in raw:
        try:
            conv = Conversation.model_validate(doc)
            msgs_dicts.append(_fmt_message(conv))
        except Exception as exc:
            logger.warning(f"poll deserialise error: {exc}")

    await _inject_media_urls(msgs_dicts)

    return {"messages": msgs_dicts}


class SendMessageBody(BaseModel):
    tg_id: int
    text:  str


@conversations_router.post("/send")
async def send_message(
    body:  SendMessageBody,
    admin: AuthUser = Depends(require_permission("admin:full")),
):
    """Send a message from the admin dashboard to a user via Telegram Bot API."""
    import httpx
    from app.core.config import settings

    if not settings.telegram_bot_token:
        raise HTTPException(503, "Bot token not configured")
    if not body.text.strip():
        raise HTTPException(400, "Empty message")

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": body.tg_id, "text": body.text, "parse_mode": "HTML"},
        )

    if not r.is_success:
        raise HTTPException(502, f"Telegram error: {r.text[:200]}")

    # Persist to conversations
    sent_data   = r.json().get("result", {})
    sent_msg_id = sent_data.get("message_id", 0)
    from app.dashboard.message_utils import store_admin_message
    asyncio.ensure_future(
        store_admin_message(body.tg_id, body.text, sent_msg_id)
    )

    from app.auth.models import AuthActivityLog
    asyncio.ensure_future(
        AuthActivityLog(
            user_id=str(admin.id), tg_id=admin.tg_id,
            action="admin.send_message",
            details={"target_tg_id": body.tg_id, "preview": body.text[:80]},
        ).insert()
    )

    return {"ok": True}
