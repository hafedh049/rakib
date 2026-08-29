"""arq worker configuration.

One background job: triage. It runs off the queue so that submitting a complaint
returns immediately instead of waiting on categorisation. The event-stream
consumer is a separate process (workers/notify_worker.py) because it consumes a
stream rather than a job queue.
"""

from typing import Any

from arq.connections import RedisSettings

from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.db import close_db, init_db
from app.services import seed_service, triage
from app.workers.triage_worker import triage_complaint

log = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    await init_db()
    await seed_service.seed_departments()
    log.info("worker.started", engine=triage.get_engine().name)


async def shutdown(ctx: dict[str, Any]) -> None:
    await close_db()
    log.info("worker.stopped")


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    functions: list = [triage_complaint]
    cron_jobs: list = []
    max_jobs = 10
    job_timeout = 120
    keep_result = 3600
