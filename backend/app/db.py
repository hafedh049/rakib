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


#: Pods start in arbitrary order under Kubernetes, so an API that exits because
#: the database is not up yet turns a five-second race into a crash loop.
STARTUP_RETRIES = 30
STARTUP_BACKOFF_SECONDS = 2


async def init_db(mongo_uri: str | None = None) -> AsyncIOMotorDatabase:
    global _client
    import asyncio

    from beanie import init_beanie

    uri = mongo_uri or settings.mongo_uri
    _client = AsyncIOMotorClient(
        uri,
        uuidRepresentation="standard",
        tz_aware=True,
        serverSelectionTimeoutMS=5_000,
    )
    database = _client.get_default_database()

    for attempt in range(1, STARTUP_RETRIES + 1):
        try:
            await _client.admin.command("ping")
            break
        except Exception as exc:
            if attempt == STARTUP_RETRIES:
                log.error("mongo.unreachable", uri_host=uri.split("@")[-1], error=str(exc))
                raise
            log.warning("mongo.waiting", attempt=attempt, error=str(exc)[:120])
            await asyncio.sleep(STARTUP_BACKOFF_SECONDS)

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
