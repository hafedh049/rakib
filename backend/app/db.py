"""Mongo connection + Beanie initialisation."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings
from app.core.logging import get_logger
from app.models import ALL_DOCUMENTS

log = get_logger(__name__)

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("Mongo client not initialised — call init_db() first")
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client().get_default_database()


async def init_db(mongo_uri: str | None = None) -> AsyncIOMotorDatabase:
    global _client
    from beanie import init_beanie

    uri = mongo_uri or settings.mongo_uri
    _client = AsyncIOMotorClient(uri, uuidRepresentation="standard", tz_aware=True)
    database = _client.get_default_database()
    await init_beanie(database=database, document_models=ALL_DOCUMENTS)
    log.info("mongo.connected", database=database.name, documents=len(ALL_DOCUMENTS))
    return database


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ping() -> bool:
    try:
        await get_client().admin.command("ping")
    except Exception:  # noqa: BLE001 — a health probe must never raise
        return False
    return True
