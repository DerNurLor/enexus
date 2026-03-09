"""
Auth database — completely separate from ncfu_schedule.
Uses the same MongoDB server but a different database: ncfu_auth.
"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from loguru import logger

from app.core.config import settings
from app.auth.models import ALL_AUTH_MODELS, _get_all_models

_auth_client: AsyncIOMotorClient | None = None


async def connect_auth_db() -> None:
    global _auth_client
    logger.info(f"Connecting auth DB → {settings.mongo_uri}/{settings.auth_mongo_db}")
    _auth_client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(
        database=_auth_client[settings.auth_mongo_db],
        document_models=_get_all_models(),
    )
    logger.info("Auth DB ready.")
    await _seed_default_roles()


async def close_auth_db() -> None:
    global _auth_client
    if _auth_client:
        _auth_client.close()
        logger.info("Auth DB closed.")


def get_auth_db():
    assert _auth_client is not None, "Auth DB not initialised"
    return _auth_client[settings.auth_mongo_db]


async def _seed_default_roles() -> None:
    """Insert default roles if they don't exist yet."""
    from app.auth.models import AuthRole
    defaults = [
        AuthRole(
            name="user",
            description="Regular authenticated user",
            permissions=["schedule:read", "floorplan:view"],
        ),
        AuthRole(
            name="beta",
            description="Beta tester with access to experimental features",
            permissions=["schedule:read", "floorplan:view", "beta_access"],
        ),
        AuthRole(
            name="admin",
            description="Full administrative access",
            permissions=["schedule:read", "schedule:write", "floorplan:view",
                         "floorplan:edit", "beta_access", "admin:full",
                         "users:read", "users:write", "logs:read"],
        ),
    ]
    for role in defaults:
        existing = await AuthRole.find_one(AuthRole.name == role.name)
        if not existing:
            await role.insert()
            logger.info(f"Seeded role: {role.name}")
