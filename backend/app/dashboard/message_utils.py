"""
dashboard/message_utils.py
Утилиты для работы с историей сообщений из дашборда — без зависимости на app.bot.
Оригинальные функции живут в ecampus_bot/app/bot/message_store.py.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from loguru import logger

from app.models.conversation import Message
from app.models.chat_settings import ChatSettings

DEFAULT_LIMIT = 300


async def store_admin_message(tg_id: int, text: str, message_id: int) -> None:
    """
    Сохраняет исходящее сообщение от администратора в историю переписки.
    Вызывается из дашборда при отправке ответа пользователю.
    """
    try:
        chat_key = f"private:{tg_id}"
        doc = Message(
            chat_id=tg_id,
            chat_key=chat_key,
            chat_type="private",
            message_id=message_id,
            role="admin",
            text=text,
            timestamp=datetime.now(timezone.utc),
        )
        await doc.insert()
    except Exception as exc:
        if "11000" in str(exc):
            return
        logger.warning(f"store_admin_message failed tg_id={tg_id}: {exc}")


async def _enforce_limit(chat_id: int, chat_key: str) -> None:
    """Обрезает историю чата до лимита, заданного в ChatSettings."""
    try:
        settings = await ChatSettings.find_one(ChatSettings.chat_id == chat_id)
        if settings is None:
            settings = ChatSettings(
                chat_id=chat_id,
                chat_key=chat_key,
                message_limit=DEFAULT_LIMIT,
            )
            await settings.insert()

        limit = settings.message_limit
        if limit is None:
            return

        count = await Message.find(Message.chat_id == chat_id).count()
        excess = count - limit
        if excess <= 0:
            return

        col = Message.get_pymongo_collection()
        cursor = col.find(
            {"chat_id": chat_id}, {"_id": 1}
        ).sort([("timestamp", 1)]).limit(excess)

        ids = [doc["_id"] async for doc in cursor]
        if ids:
            await col.delete_many({"_id": {"$in": ids}})

        settings.last_cleaned_at = datetime.now(timezone.utc)
        await settings.save()

    except Exception as exc:
        logger.warning(f"_enforce_limit failed chat_id={chat_id}: {exc}")
