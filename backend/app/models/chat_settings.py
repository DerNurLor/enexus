from __future__ import annotations
from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field


class ChatSettings(Document):
    chat_id: Indexed(int, unique=True)
    chat_key: str
    chat_type: str = 'private'
    title: Optional[str] = None
    username: Optional[str] = None

    message_limit: Optional[int] = 300
    time_limit_days: Optional[int] = None

    # None = использовать глобальные настройки из config/settings
    bot_quota_cap: Optional[int] = None
    bot_quota_ttl_hours: Optional[int] = None

    logging_enabled: bool = True
    last_cleaned_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


    class Settings:
        name = 'chat_settings'
