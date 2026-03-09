from __future__ import annotations
from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field


class ChatSettings(Document):
    chat_id: Indexed(int, unique=True)  # первичный ключ
    chat_key: str                        # '{chat_id}:{thread_id or 0}'
    chat_type: str = 'private'           # private|group|supergroup|channel
    title: Optional[str] = None          # название группы/канала
    username: Optional[str] = None       # @username группы


    # ── Лимиты хранения сообщений ────────────────────────────────────────
    message_limit: Optional[int] = 300   # None = бесконечно
    time_limit_days: Optional[int] = None # TTL в днях (None = без ограничения)

    # ── Лимиты бота (AI-запросы) ─────────────────────────────────────────
    # None = использовать глобальные настройки из config/settings
    bot_quota_cap: Optional[int] = None       # макс. запросов за период (None = global)
    bot_quota_ttl_hours: Optional[int] = None # длина периода в часах (None = global)

    # ── Статус ─────────────────────────────────────────────────────────
    logging_enabled: bool = True
    last_cleaned_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


    class Settings:
        name = 'chat_settings'
