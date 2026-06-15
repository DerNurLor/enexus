"""
Conversation — full per-message record for every user↔bot exchange.

Stored in:  ncfu_auth  →  collection "conversations"

Design decisions:
- One document per Telegram message (not per user).  This keeps queries fast
  and avoids ever hitting the 16 MB BSON document limit on active chats.
- All media is stored as metadata only (file_id + useful dimensions/duration).
  Actual bytes are fetched on-demand from the Telegram CDN and cached in Redis.
- The `media` sub-document is None for text-only messages, making it easy to
  filter "messages with attachments" via   {"media": {"$ne": null}}.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel


MediaKind = Literal[
"photo", "video", "animation", "sticker",
"voice", "video_note", "audio", "document",
]


class MediaMeta(BaseModel):
    """Telegram media attachment metadata — no binary data stored here."""

    kind: MediaKind

    file_id: str
    file_unique_id: str

    file_size: Optional[int] = None
    mime_type: Optional[str] = None

    width:  Optional[int] = None
    height: Optional[int] = None

    duration: Optional[int] = None  # seconds

    file_name: Optional[str] = None
    title:     Optional[str] = None
    performer: Optional[str] = None

    sticker_emoji:     Optional[str]  = None
    sticker_type:      Optional[str]  = None
    sticker_set_name:  Optional[str]  = None

    thumbnail_file_id: Optional[str] = None



class ForwardOrigin(BaseModel):
    """Parsed forward_origin — we store only display-relevant fields."""
    kind:      str             # "user" | "hidden_user" | "chat" | "channel"
    name:      Optional[str] = None   # sender display name or channel title
    tg_id:     Optional[int] = None   # sender user / chat id if known
    date:      Optional[datetime] = None



class Message(Document):
    """
    One Telegram message in the conversation history.

    Indexed access patterns:
      - list all messages for a user, newest-first   → (tg_id, -timestamp)
      - paginate a chat by cursor                     → (tg_id, message_id)
      - filter by media kind                          → (tg_id, media.kind)
      - admin search by text                          → $text index on `text`
    """

    chat_id: Indexed(int)
    chat_key: Indexed(str)
    chat_type: str = 'private'
    thread_id: Optional[int] = None

    tg_id:      Indexed(int)   # type: ignore[valid-type]
    message_id: int
    edited_at: Optional[datetime] = None

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    # "user" = incoming, "bot" = outgoing reply, "admin" = sent from dashboard
    role: str = 'user'
    message_type: str = 'text'
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    text:      Optional[str] = ""
    # HTML-formatted version (bold/italic/code etc. preserved as HTML tags)
    html_text: Optional[str] = ""
    entities:  list[dict] = Field(default_factory=list)

    media: Optional[MediaMeta] = None

    forward: Optional[ForwardOrigin] = None

    reply_to_message_id: Optional[int] = None
    reply_to_text:       Optional[str] = None   # short preview of replied msg

    extra: Optional[dict] = None

    class Settings:
        name = "conversations"
        indexes = [
            IndexModel(
                [("tg_id", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_tg_id_ts"
            ),

            IndexModel(
                [("tg_id", ASCENDING), ("message_id", ASCENDING)],
                unique=True,
                name="idx_uniq_tg_msg_id"
            ),

            IndexModel(
                [("tg_id", ASCENDING), ("media.kind", ASCENDING)],
                name="idx_tg_media_kind",
                sparse=True
            ),

            IndexModel(
                [("timestamp", ASCENDING)],
                expireAfterSeconds=60 * 60 * 24 * 180,
                name="idx_timestamp_ttl"
            ),

            IndexModel(
                [("chat_id", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_chat_id_timestamp"
            ),
        ]
