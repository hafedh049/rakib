"""The six-stage pipeline.

    normalize -> language -> classify -> rules/priority -> dedup -> decide

Stages one to four live inside the engine (they are inseparable from the model
it holds). This module adds dedup, records the stage timings, and returns a
single enriched TriageOutput. The `decide` stage — thresholds, routing
fallbacks, SLA — lives in services/triage_service.py, because it is policy, not
inference.

Target end to end: under 50 ms.
"""

import time
from dataclasses import replace

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.dedup.detector import DedupMatch, detect
from app.intelligence.ports import TriageEngine, TriageInput, TriageOutput

log = get_logger(__name__)


async def run(
    engine: TriageEngine, data: TriageInput
) -> tuple[TriageOutput, list[DedupMatch]]:
    started = time.perf_counter()

    output = await engine.analyze(data)

    mark = time.perf_counter()
    duplicate, suggestions = detect(
        output.normalized_text,
        data.subject,
        data.recent_complaints,
        claimant_email=data.claimant_email,
        auto_threshold=settings.dedup_auto_threshold,
        suggest_threshold=settings.dedup_suggest_threshold,
        cross_claimant_threshold=settings.dedup_cross_claimant_threshold,
    )
    dedup_stage = {
        "name": "dedup",
        "latency_ms": round((time.perf_counter() - mark) * 1000, 2),
        "output_summary": {
            "candidates": len(data.recent_complaints),
            "duplicate": duplicate.candidate_id if duplicate else None,
            "score": duplicate.score if duplicate else None,
            "suggestions": len(suggestions),
        },
    }

    enriched = replace(
        output,
        duplicate_of_id=(
            duplicate.candidate_id
            if duplicate and duplicate.relation == "duplicate"
            else None
        ),
        duplicate_score=duplicate.score if duplicate else None,
        # A cross-claimant match is an incident cluster, not a duplicate, so it
        # is recorded as related and never suppresses the complaint.
        related_ids=[
            match.candidate_id
            for match in ([duplicate] if duplicate else []) + suggestions
            if match.relation == "related"
        ],
        stages=[*output.stages, dedup_stage],
        latency_ms=int((time.perf_counter() - started) * 1000),
    )

    log.info(
        "pipeline.completed",
        engine=enriched.engine,
        category=enriched.category,
        priority=enriched.priority,
        latency_ms=enriched.latency_ms,
    )
    return enriched, suggestions
