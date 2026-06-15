"""
Auth database models — stored in a SEPARATE database (ncfu_auth).
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class AuthRole(Document):
    name: Indexed(str, unique=True)  # type: ignore[valid-type]
    description: str = ""
    permissions: list[str] = Field(default_factory=list)
    rate_limit_rpm: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "auth_roles"
        indexes = [IndexModel([("name", ASCENDING)], unique=True)]


class AuthUser(Document):
    tg_id: Indexed(int, unique=True)  # type: ignore[valid-type]
    username: Optional[str] = None
    first_name: str = ""
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    photo_url: Optional[str] = None
    photo_local_path: Optional[str] = None
    roles: list[str] = Field(default_factory=lambda: ["user"])
    is_blocked: bool = False
    block_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    miniapp_favorites: list[dict] = Field(default_factory=list)
    miniapp_settings:  dict       = Field(default_factory=dict)
    totp_secret:    Optional[str] = None
    totp_enabled:   bool = False
    extra_permissions: list[str] = Field(default_factory=list)
    accent_color: str = "#7c6eff"
    daily_requests:       Optional[int] = None
    monthly_ai_tokens:    Optional[int] = None
    ai_tokens_used_today: int = 0
    ai_tokens_used_month: int = 0

    class Settings:
        name = "auth_users"
        indexes = [
            IndexModel([("tg_id", ASCENDING)], unique=True),
            IndexModel([("username", ASCENDING)]),
            IndexModel([("last_active", DESCENDING)]),
            IndexModel([("is_blocked", ASCENDING)]),
        ]

    def has_permission(self, permission: str) -> bool:
        return False


class AuthApiKey(Document):
    key_hash: str
    key_prefix: str
    user_id: Indexed(str)  # type: ignore[valid-type]
    name: str = "default"
    permissions: list[str] = Field(default_factory=list)
    rate_limit_rpm: int = 60
    expires_at: Optional[datetime] = None
    is_revoked: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    use_count: int = 0

    class Settings:
        name = "auth_api_keys"
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("key_prefix", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)]),
            IndexModel([("is_revoked", ASCENDING)]),
        ]


class AuthActivityLog(Document):
    user_id: Optional[str] = None
    tg_id: Optional[int] = None
    action: str
    request_id: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "auth_activity_log"
        indexes = [
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("tg_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("action", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", DESCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=60*60*24*90, name="activity_ttl"),
        ]


class AuthErrorLog(Document):
    level: str
    message: str
    traceback: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    path: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "auth_error_logs"
        indexes = [
            IndexModel([("level", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", DESCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=60*60*24*30, name="error_ttl"),
        ]


class BotConversation(Document):
    """Per-user conversation history for context-aware AI (stored in Redis primarily, synced here)."""
    tg_id: Indexed(int, unique=True)  # type: ignore[valid-type]
    messages: list[dict] = Field(default_factory=list)  # [{role, content, ts}]
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "bot_conversations"
        indexes = [
            IndexModel([("tg_id", ASCENDING)], unique=True),
            IndexModel([("updated_at", DESCENDING)]),
        ]


class ChatMessage(Document):
    """
    Full Telegram message record — every user↔bot exchange stored here.
    This is the source of truth for the dashboard conversation viewer.
    Media files are NOT stored on disk automatically — only metadata.
    Admin can fetch any file on-demand via file_id.
    """
    tg_id:      Indexed(int)   # type: ignore[valid-type]  — user's Telegram ID
    message_id: int            # Telegram message_id (unique per chat)
    role:       str            # "user" | "bot" | "bot_reply"
    timestamp:  datetime = Field(default_factory=datetime.utcnow)

    # Text content (may include HTML formatting)
    text:      str  = ""
    html_text: str  = ""   # formatted version (bold/italic/code preserved as HTML)

    # Forward info
    is_forward:          bool = False
    forward_from_name:   Optional[str] = None
    forward_from_id:     Optional[int] = None
    forward_from_chat:   Optional[str] = None   # channel/group title
    forward_date:        Optional[datetime] = None

    # Reply-to info
    reply_to_message_id: Optional[int] = None
    reply_to_text:       Optional[str] = None   # short preview of replied message

    # Media metadata (no binary stored — fetch on demand via file_id)
    media_type:     Optional[str] = None   # photo|video|document|voice|audio|sticker|animation
    file_id:        Optional[str] = None   # Telegram file_id for on-demand download
    file_unique_id: Optional[str] = None
    file_name:      Optional[str] = None
    file_size:      Optional[int] = None
    mime_type:      Optional[str] = None
    duration:       Optional[int] = None   # seconds (voice/video/audio)
    width:          Optional[int] = None
    height:         Optional[int] = None
    thumbnail_file_id: Optional[str] = None

    # Sticker extras
    sticker_emoji:  Optional[str] = None

    # Inline entities (links, mentions, etc.) — as parsed JSON
    entities: list[dict] = Field(default_factory=list)

    class Settings:
        name = "chat_messages"
        indexes = [
            IndexModel([("tg_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("tg_id", ASCENDING), ("message_id", ASCENDING)], unique=True,
                       name="uniq_tg_msg", background=True),
            IndexModel([("timestamp", DESCENDING)]),
            IndexModel([("role", ASCENDING), ("timestamp", DESCENDING)]),
            # TTL: keep messages for 180 days
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=60*60*24*180, name="msg_ttl"),
        ]


class SupportTicket(Document):
    tg_id: int
    username: Optional[str] = None
    first_name: str = ""
    message: str
    status: str = "open"        # open | answered | closed
    category: str = "other"     # bug | suggestion | question | other
    source: str = "bot"         # bot | miniapp
    admin_reply: Optional[str] = None
    replied_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    close_reason_hidden: bool = False   # hide reason from user
    closed_by: Optional[str] = None    # "user" | "admin" | "timeout"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def short_id(self) -> str:
        return str(self.id)[:8] if self.id else "?"

    class Settings:
        name = "support_tickets"
        indexes = [
            IndexModel([("tg_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("category", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]


class BroadcastJob(Document):
    text: str
    audience: str = "all"   # all | active | role
    role: Optional[str] = None
    schedule_at: Optional[datetime] = None
    status: str = "pending"   # pending | running | done | failed
    sent_count: int = 0
    total_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Settings:
        name = "broadcast_jobs"
        indexes = [
            IndexModel([("status", ASCENDING), ("schedule_at", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]


class AuthDPoPNonce(Document):
    nonce: Indexed(str, unique=True)  # type: ignore[valid-type]
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    used: bool = False

    class Settings:
        name = "auth_dpop_nonces"
        indexes = [
            IndexModel([("nonce", ASCENDING)], unique=True),
            IndexModel([("issued_at", ASCENDING)], expireAfterSeconds=600, name="nonce_ttl"),
        ]


ALL_AUTH_MODELS = [
    AuthRole, AuthUser, AuthApiKey,
    AuthActivityLog, AuthErrorLog,
    BotConversation, ChatMessage, SupportTicket, BroadcastJob,
    AuthDPoPNonce,
]
