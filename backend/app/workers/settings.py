"""arq worker configuration.

Background jobs and cron live here: triage (phase 6), SLA sweeps (phase 7) and
retraining (phase 9) are registered as they land. The event-stream consumer is a
separate process (workers/notify_worker.py) because it is a stream consumer, not
a job queue.
"""

from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.db import close_db, init_db
from app.services import rules_service, seed_service, triage
from app.workers.retrain_worker import check_retrain_trigger, retrain_model
from app.workers.sla_worker import sweep_sla
from app.workers.triage_worker import triage_complaint

log = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    await init_db()
    await seed_service.seed_departments()
    await rules_service.seed_rules()
    await triage.refresh_rules()
    log.info("worker.started", engine=triage.get_engine().name)


async def shutdown(ctx: dict[str, Any]) -> None:
    await close_db()
    log.info("worker.stopped")


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    functions: list = [triage_complaint, sweep_sla, retrain_model,
                       check_retrain_trigger]
    cron_jobs: list = [
        # Every five minutes: SLA budgets are hours, so finer granularity buys
        # nothing and costs a database scan.
        cron(sweep_sla, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
        # Checks the correction count; only trains if the threshold is met.
        cron(check_retrain_trigger, hour={3}, minute={17}),
    ]
    max_jobs = 10
    job_timeout = 120
    keep_result = 3600
