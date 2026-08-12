"""Scheduled SLA sweep.

Runs every five minutes rather than every minute: SLA budgets are measured in
hours, and a five-minute granularity on a 4-hour deadline is 2% of the budget —
far below the noise floor, and a fifth of the database load.
"""

from typing import Any

from app.core.logging import get_logger
from app.services import sla_service

log = get_logger(__name__)


async def sweep_sla(ctx: dict[str, Any]) -> dict[str, int]:
    result = await sla_service.sweep()
    return result
