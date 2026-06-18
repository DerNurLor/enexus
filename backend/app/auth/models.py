from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthRole(Document):
    name: Indexed(str, unique=True)  # type: ignore[valid-type]
    description: str = ""
    permissions: list[str] = Field(default_factory=list)
    rate_limit_rpm: Optional[int] = None
    created_at: datetime = Field(default_factory=_utcnow)

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
    created_at: datetime = Field(default_factory=_utcnow)
    last_active: datetime = Field(default_factory=_utcnow)
    miniapp_favorites: list[dict] = Field(default_factory=list)
    miniapp_settings:  dict       = Field(default_factory=dict)
    totp_secret:    Optional[str] = None
    totp_enabled:   bool = False
    # Per-user direct permissions (added on top of role permissions)
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
        """Checks direct extra_permissions only; use _user_permissions() from dependencies for role-based checks."""
        return permission in self.extra_permissions


class AuthApiKey(Document):
    key_hash: str
    key_prefix: str
    user_id: Indexed(str)  # type: ignore[valid-type]
    name: str = "default"
    permissions: list[str] = Field(default_factory=list)
    rate_limit_rpm: int = 60
    expires_at: Optional[datetime] = None
    is_revoked: bool = False
    created_at: datetime = Field(default_factory=_utcnow)
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
    timestamp: datetime = Field(default_factory=_utcnow)
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
    timestamp: datetime = Field(default_factory=_utcnow)
    error_id: Optional[str] = None
    tg_id: Optional[int] = None
    tg_chat_id: Optional[int] = None
    user_text: Optional[str] = None
    intent: Optional[str] = None

    class Settings:
        name = "auth_error_logs"
        indexes = [
            IndexModel([("level", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", DESCENDING)]),
            IndexModel([("error_id", ASCENDING)], sparse=True, name="idx_error_id"),
            IndexModel([("tg_id", ASCENDING), ("timestamp", DESCENDING)], sparse=True, name="idx_tg_id_err"),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=60*60*24*30, name="error_ttl"),
        ]


class BotConversation(Document):
    tg_id: Indexed(int, unique=True)  # type: ignore[valid-type]
    messages: list[dict] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=_utcnow)
    class Settings:
        name = "bot_conversations"
        indexes = [
            IndexModel([("tg_id", ASCENDING)], unique=True),
            IndexModel([("updated_at", DESCENDING)]),
        ]


class ChatMessage(Document):
    tg_id:      Indexed(int)   # type: ignore[valid-type]
    message_id: int
    role:       str
    timestamp:  datetime = Field(default_factory=_utcnow)
    text:      str  = ""
    html_text: str  = ""

    is_forward:          bool = False
    forward_from_name:   Optional[str] = None
    forward_from_id:     Optional[int] = None
    forward_from_chat:   Optional[str] = None
    forward_date:        Optional[datetime] = None

    reply_to_message_id: Optional[int] = None
    reply_to_text:       Optional[str] = None

    media_type:     Optional[str] = None
    file_id:        Optional[str] = None
    file_unique_id: Optional[str] = None
    file_name:      Optional[str] = None
    file_size:      Optional[int] = None
    mime_type:      Optional[str] = None
    duration:       Optional[int] = None
    width:          Optional[int] = None
    height:         Optional[int] = None
    thumbnail_file_id: Optional[str] = None

    sticker_emoji:  Optional[str] = None
    entities: list[dict] = Field(default_factory=list)

    class Settings:
        name = "chat_messages"
        indexes = [
            IndexModel([("tg_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("tg_id", ASCENDING), ("message_id", ASCENDING)], unique=True,
                       name="uniq_tg_msg", background=True),
            IndexModel([("timestamp", DESCENDING)]),
            IndexModel([("role", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=60*60*24*180, name="msg_ttl"),
        ]


class SupportTicket(Document):
    tg_id: int
    username: Optional[str] = None
    first_name: str = ""
    message: str
    status: str = "open"
    category: str = "other"
    source: str = "bot"
    admin_reply: Optional[str] = None
    replied_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    close_reason_hidden: bool = False
    closed_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
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
    audience: str = "all"
    role: Optional[str] = None
    schedule_at: Optional[datetime] = None
    status: str = "pending"
    sent_count: int = 0
    total_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
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
    issued_at: datetime = Field(default_factory=_utcnow)
    used: bool = False

    class Settings:
        name = "auth_dpop_nonces"
        indexes = [
            IndexModel([("nonce", ASCENDING)], unique=True),
            IndexModel([("issued_at", ASCENDING)], expireAfterSeconds=600, name="nonce_ttl"),
        ]


class BotFeedback(Document):
    chat_id:    Indexed(int)   # type: ignore[valid-type]
    message_id: Indexed(int)   # type: ignore[valid-type]
    tg_id:      int

    user_text: str = ""
    bot_text:  str = ""

    rating: Optional[str] = None
    status: str = "pending"

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    class Settings:
        name = "bot_feedback"
        indexes = [
            IndexModel(
                [("chat_id", ASCENDING), ("message_id", ASCENDING)],
                unique=True,
                name="idx_chat_msg_uniq",
            ),
            IndexModel([("tg_id", ASCENDING)]),
            IndexModel([("rating", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]


ALL_AUTH_MODELS = [
    AuthRole, AuthUser, AuthApiKey,
    AuthActivityLog, AuthErrorLog,
    BotConversation, ChatMessage, SupportTicket, BroadcastJob,
    AuthDPoPNonce, BotFeedback,
]


def _get_all_models():
    from app.models.conversation import Message
    from app.models.chat_settings import ChatSettings
    return ALL_AUTH_MODELS + [Message, ChatSettings]
