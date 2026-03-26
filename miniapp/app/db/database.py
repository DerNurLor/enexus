from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from loguru import logger
from app.core.config import settings
from app.models.lesson import LessonDoc
from app.models.group import Group
from app.models.teacher import Teacher
from app.models.room import Room
from app.models.institute import Institute
from app.models.scrape_log import ScrapeLog

_client: AsyncIOMotorClient | None = None

async def connect_db() -> None:
    global _client
    logger.info(f"Connecting to MongoDB at {settings.mongo_uri}...")
    _client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(
        database=_client.get_database(settings.mongo_db),
        document_models=[LessonDoc, Institute, Group, Teacher, Room, ScrapeLog],
    )
    logger.info("MongoDB ready.")

async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB closed.")

def get_motor_db():
    assert _client is not None
    return _client.get_database(settings.mongo_db)
