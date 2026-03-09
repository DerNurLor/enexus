"""
dashboard/app/db/database.py

Lightweight connection to the schedule MongoDB database.
Dashboard only uses raw Motor collections (no Beanie models needed for schedule data).
"""
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    global _client
    logger.info(f"Connecting schedule DB → {settings.auth_mongo_uri}/{settings.mongo_db}")
    _client = AsyncIOMotorClient(settings.auth_mongo_uri)
    # No beanie init needed — dashboard uses raw Motor for schedule collections
    logger.info("Schedule DB ready (raw Motor).")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        logger.info("Schedule DB closed.")


def get_motor_db():
    assert _client is not None, "Schedule DB not initialised"
    return _client[settings.mongo_db]
