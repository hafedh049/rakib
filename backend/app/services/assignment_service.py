"""Deterministic agent assignment. No ML — the spec is explicit about that.

    score = 0.5 * (1 - open_count / max_concurrent)
          + 0.3 * skill_match(agent.skills, category)
          + 0.2 * recency(last_active_at)

Ties break on the lowest open count, then the lowest user id, so the same inputs
always produce the same assignment. That matters more than cleverness here: a
supervisor has to be able to explain why a complaint landed on a given desk.
"""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from app.core.logging import get_logger
from app.models.complaint import CLOSED_STATUSES, Complaint
from app.models.department import Department
from app.models.user import Role, User

log = get_logger(__name__)

WEIGHT_LOAD = 0.5
WEIGHT_SKILL = 0.3
WEIGHT_RECENCY = 0.2

#: Beyond this, "recently active" stops meaning anything.
RECENCY_HORIZON_HOURS = 72


async def open_counts(
    agent_ids: list[PydanticObjectId],
) -> dict[PydanticObjectId | None, int]:
    """Open complaints per agent. Keys are Optional because Beanie ids are."""
    if not agent_ids:
        return {}
    pipeline = [
        {
            "$match": {
                "assignment.agent_id": {"$in": agent_ids},
                "status": {"$nin": [str(s) for s in CLOSED_STATUSES]},
            }
        },
        {"$group": {"_id": "$assignment.agent_id", "count": {"$sum": 1}}},
    ]
    rows = await Complaint.aggregate(pipeline).to_list()
    return {row["_id"]: row["count"] for row in rows}


def skill_match(skills: list[str], category: str | None) -> float:
    """Fraction of the category's tokens covered by the agent's skills."""
    if not category or not skills:
        return 0.0
    tokens = {part for part in category.lower().split("_") if len(part) > 2}
    if not tokens:
        return 0.0
    lowered = " ".join(skills).lower()
    return sum(1 for token in tokens if token in lowered) / len(tokens)


def recency(last_active_at: datetime | None, now: datetime | None = None) -> float:
    if last_active_at is None:
        return 0.0
    moment = now or datetime.now(UTC)
    if last_active_at.tzinfo is None:
        last_active_at = last_active_at.replace(tzinfo=UTC)
    hours = (moment - last_active_at).total_seconds() / 3600
    if hours <= 0:
        return 1.0
    return max(0.0, 1.0 - hours / RECENCY_HORIZON_HOURS)


def score_agent(
    agent: User, open_count: int, category: str | None, now: datetime | None = None
) -> float:
    capacity = max(1, agent.max_concurrent)
    load = max(0.0, 1.0 - open_count / capacity)
    return (
        WEIGHT_LOAD * load
        + WEIGHT_SKILL * skill_match(agent.skills, category)
        + WEIGHT_RECENCY * recency(agent.last_active_at, now)
    )


async def pick_agent(
    department: Department, category: str | None, now: datetime | None = None
) -> User | None:
    """Best available agent in the department, or None to leave it queued."""
    agents = await User.find(
        {
            "department_id": department.id,
            "role": str(Role.AGENT),
            "is_active": True,
        }
    ).to_list()
    if not agents:
        return None

    counts = await open_counts([agent.id for agent in agents if agent.id])
    available = [
        agent
        for agent in agents
        if counts.get(agent.id, 0) < max(1, agent.max_concurrent)
    ]
    if not available:
        log.info("assignment.all_at_capacity", department=department.code)
        return None

    ranked = sorted(
        available,
        key=lambda agent: (
            -score_agent(agent, counts.get(agent.id, 0), category, now),
            counts.get(agent.id, 0),
            str(agent.id),
        ),
    )
    return ranked[0]
