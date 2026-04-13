from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie
from loguru import logger

from app.core.config import settings
from app.models.lesson import LessonDoc
from app.models.group import Group
from app.models.teacher import Teacher
from app.models.room import Room
from app.models.institute import Institute
from app.models.scrape_log import ScrapeLog
from app.models.campus import Campus
from app.ecampus.sync_service import ECampusSyncRecord

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    global _client
    logger.info(f"Connecting to MongoDB at {settings.mongo_uri}...")
    _client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(
        database=_client.get_database(settings.mongo_db),
        document_models=[LessonDoc, Institute, Group, Teacher, Room, ScrapeLog, ECampusSyncRecord, Campus],
    )
    logger.info("MongoDB ready.")


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed.")


def get_motor_db() -> AsyncIOMotorDatabase:
    """Возвращает объект базы данных Motor для прямых запросов через коллекции."""
    assert _client is not None, "Database not connected. Call connect_db() first."
    return _client.get_database(settings.mongo_db)
