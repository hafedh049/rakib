"""Aggregation pipelines behind /analytics.

Everything runs in Mongo rather than in Python: the console polls these on every
dashboard load, and pulling thousands of complaints into the API process to count
them would be the first thing to fall over under load.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.logging import get_logger
from app.models.complaint import CLOSED_STATUSES, Complaint, Status
from app.models.kb_article import KBArticle
from app.models.rule import Rule
from app.models.user import Role, User

log = get_logger(__name__)

DEFAULT_WINDOW_DAYS = 30


def _since(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


async def overview(days: int = DEFAULT_WINDOW_DAYS) -> dict[str, Any]:
    since = _since(days)
    window = {"created_at": {"$gte": since}}

    by_status = {
        row["_id"]: row["count"]
        for row in await Complaint.aggregate(
            [{"$match": window}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        ).to_list()
    }
    by_priority = {
        str(row["_id"]): row["count"]
        for row in await Complaint.aggregate(
            [
                {"$match": {**window, "analysis.priority": {"$ne": None}}},
                {"$group": {"_id": "$analysis.priority", "count": {"$sum": 1}}},
            ]
        ).to_list()
    }

    resolution = await Complaint.aggregate(
        [
            {
                "$match": {
                    **window,
                    "sla.resolved_at": {"$ne": None},
                }
            },
            {
                "$project": {
                    "hours": {
                        "$divide": [
                            {"$subtract": ["$sla.resolved_at", "$created_at"]},
                            3_600_000,
                        ]
                    }
                }
            },
            {"$group": {"_id": None, "avg": {"$avg": "$hours"}, "n": {"$sum": 1}}},
        ]
    ).to_list()

    total = sum(by_status.values())
    breached = await Complaint.find({**window, "sla.breached": True}).count()
    closed = sum(by_status.get(str(s), 0) for s in CLOSED_STATUSES)
    needs_triage = await Complaint.find(
        {**window, "analysis.needs_human_triage": True}
    ).count()
    duplicates = await Complaint.find(
        {**window, "analysis.duplicate_of": {"$ne": None}}
    ).count()

    satisfaction = await Complaint.aggregate(
        [
            {"$match": {**window, "satisfaction": {"$ne": None}}},
            {
                "$group": {
                    "_id": None,
                    "avg": {"$avg": "$satisfaction.score"},
                    "n": {"$sum": 1},
                }
            },
        ]
    ).to_list()

    return {
        "window_days": days,
        "total": total,
        "open": total - closed,
        "closed": closed,
        "by_status": by_status,
        "by_priority": by_priority,
        "sla": {
            "breached": breached,
            # Compliance is measured against everything in the window, not just
            # what closed: a complaint sitting past its deadline is a breach now,
            # not when someone finally resolves it.
            "compliance_rate": round(1 - (breached / total), 4) if total else 1.0,
        },
        "avg_resolution_hours": (
            round(float(resolution[0]["avg"]), 2) if resolution else None
        ),
        "resolved_count": resolution[0]["n"] if resolution else 0,
        "needs_human_triage": needs_triage,
        "duplicates_detected": duplicates,
        "satisfaction": {
            "average": round(float(satisfaction[0]["avg"]), 2) if satisfaction else None,
            "responses": satisfaction[0]["n"] if satisfaction else 0,
        },
    }


async def by_category(days: int = DEFAULT_WINDOW_DAYS) -> list[dict[str, Any]]:
    rows = await Complaint.aggregate(
        [
            {"$match": {"created_at": {"$gte": _since(days)},
                        "analysis.category": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$analysis.category",
                    "count": {"$sum": 1},
                    "avg_priority": {"$avg": "$analysis.priority"},
                    "breached": {"$sum": {"$cond": ["$sla.breached", 1, 0]}},
                    "avg_confidence": {"$avg": "$analysis.category_confidence"},
                }
            },
            {"$sort": {"count": -1}},
        ]
    ).to_list()
    return [
        {
            "category": row["_id"],
            "count": row["count"],
            "avg_priority": round(float(row["avg_priority"] or 0), 2),
            "breached": row["breached"],
            "avg_confidence": round(float(row["avg_confidence"] or 0), 3),
        }
        for row in rows
    ]


async def volume_by_day(days: int = DEFAULT_WINDOW_DAYS) -> list[dict[str, Any]]:
    rows = await Complaint.aggregate(
        [
            {"$match": {"created_at": {"$gte": _since(days)}}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    },
                    "count": {"$sum": 1},
                    "breached": {"$sum": {"$cond": ["$sla.breached", 1, 0]}},
                }
            },
            {"$sort": {"_id": 1}},
        ]
    ).to_list()
    return [
        {"date": row["_id"], "count": row["count"], "breached": row["breached"]}
        for row in rows
    ]


async def agents(days: int = DEFAULT_WINDOW_DAYS) -> list[dict[str, Any]]:
    rows = await Complaint.aggregate(
        [
            {"$match": {"created_at": {"$gte": _since(days)},
                        "assignment.agent_id": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$assignment.agent_id",
                    "total": {"$sum": 1},
                    "resolved": {
                        "$sum": {
                            "$cond": [
                                {"$in": ["$status", [str(s) for s in CLOSED_STATUSES]]},
                                1, 0,
                            ]
                        }
                    },
                    "breached": {"$sum": {"$cond": ["$sla.breached", 1, 0]}},
                    "satisfaction": {"$avg": "$satisfaction.score"},
                }
            },
            {"$sort": {"total": -1}},
        ]
    ).to_list()

    staff = {
        user.id: user
        for user in await User.find({"role": {"$ne": str(Role.CLAIMANT)}}).to_list()
    }
    return [
        {
            "agent_id": str(row["_id"]),
            "name": staff[row["_id"]].full_name if row["_id"] in staff else "—",
            "total": row["total"],
            "resolved": row["resolved"],
            "open": row["total"] - row["resolved"],
            "breached": row["breached"],
            "satisfaction": (
                round(float(row["satisfaction"]), 2) if row["satisfaction"] else None
            ),
        }
        for row in rows
    ]


async def engine_report() -> dict[str, Any]:
    """How often the engine is overruled, and at what confidence.

    Article 9 requires key performance indicators. The correction rate is the
    honest one: the share of automatic categorisations an agent had to change.
    Read together with the confidence buckets it also validates the abstention
    thresholds — if the lowest bucket is rarely corrected, the engine is being
    too cautious; if the highest bucket is often corrected, too bold.
    """
    total_triaged = await Complaint.find({"analysis.category": {"$ne": None}}).count()
    corrected = await Complaint.find({"corrected": True}).count()

    confidence_rows = await Complaint.aggregate(
        [
            {"$match": {"analysis.category_confidence": {"$ne": None}}},
            {
                "$bucket": {
                    "groupBy": "$analysis.category_confidence",
                    "boundaries": [0, 0.25, 0.45, 0.55, 0.7, 0.85, 1.01],
                    "default": "other",
                    "output": {
                        "count": {"$sum": 1},
                        "corrected": {"$sum": {"$cond": ["$corrected", 1, 0]}},
                    },
                }
            },
        ]
    ).to_list()

    return {
        "corrections": {
            "triaged": total_triaged,
            "corrected": corrected,
            # The headline number: how often a human disagreed with the engine.
            "correction_rate": (
                round(corrected / total_triaged, 4) if total_triaged else 0.0
            ),
        },
        "confidence_buckets": [
            {
                "from": row["_id"] if isinstance(row["_id"], int | float) else None,
                "count": row["count"],
                "corrected": row["corrected"],
            }
            for row in confidence_rows
        ],
    }


async def rules_report(days: int = DEFAULT_WINDOW_DAYS) -> list[dict[str, Any]]:
    """Which rules fire most, and whether the complaints they fire on breach."""
    rows = await Complaint.aggregate(
        [
            {"$match": {"created_at": {"$gte": _since(days)},
                        "analysis.rule_hits": {"$ne": []}}},
            {"$unwind": "$analysis.rule_hits"},
            {
                "$group": {
                    "_id": "$analysis.rule_hits.code",
                    "fires": {"$sum": 1},
                    "avg_weight": {"$avg": "$analysis.rule_hits.weight"},
                    "avg_priority": {"$avg": "$analysis.priority"},
                    "breached": {"$sum": {"$cond": ["$sla.breached", 1, 0]}},
                }
            },
            {"$sort": {"fires": -1}},
        ]
    ).to_list()

    labels = {rule.code: rule for rule in await Rule.find_all().to_list()}
    return [
        {
            "code": row["_id"],
            "label": labels[row["_id"]].label if row["_id"] in labels else row["_id"],
            "active": labels[row["_id"]].active if row["_id"] in labels else None,
            "weight": labels[row["_id"]].weight if row["_id"] in labels else None,
            "fires": row["fires"],
            "avg_applied_weight": round(float(row["avg_weight"] or 0), 2),
            "avg_priority": round(float(row["avg_priority"] or 0), 2),
            "breach_rate": (
                round(row["breached"] / row["fires"], 4) if row["fires"] else 0.0
            ),
        }
        for row in rows
    ]


async def kb_report() -> list[dict[str, Any]]:
    articles = await KBArticle.find_all().sort("-usage_count").to_list()
    return [
        {
            "id": str(article.id),
            "title": article.title,
            "category": article.category,
            "language": article.language,
            "usage_count": article.usage_count,
            "breakdown": article.usage_breakdown,
        }
        for article in articles
    ]


async def supervision_board() -> dict[str, Any]:
    """The three queues a supervisor actually watches."""
    open_filter = {"status": {"$nin": [str(s) for s in CLOSED_STATUSES]}}
    return {
        "breached": await Complaint.find(
            {**open_filter, "sla.breached": True}
        ).count(),
        "at_risk": await Complaint.find(
            {**open_filter, "sla.warned": True, "sla.breached": False}
        ).count(),
        "unassigned": await Complaint.find(
            {**open_filter, "assignment.agent_id": None}
        ).count(),
        "needs_triage": await Complaint.find(
            {**open_filter, "analysis.needs_human_triage": True}
        ).count(),
        "new": await Complaint.find({"status": str(Status.NEW)}).count(),
    }
