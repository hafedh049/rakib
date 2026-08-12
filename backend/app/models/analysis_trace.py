from datetime import UTC, datetime
from typing import Any

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class TraceStage(BaseModel):
    name: str
    latency_ms: float
    output_summary: dict[str, Any] = Field(default_factory=dict)


class AnalysisTrace(Document):
    """One row per triage attempt — the audit trail behind every decision.

    Kept separate from the complaint so a re-triage does not overwrite the
    history of what the previous model version decided and why.
    """

    complaint_id: PydanticObjectId
    complaint_ref: str
    engine: str
    model_version: str
    stages: list[TraceStage] = Field(default_factory=list)
    total_latency_ms: int = 0
    outcome: str = "ok"          # ok | failed | skipped
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "analysis_traces"
        indexes = [
            pymongo.IndexModel(
                [("complaint_id", 1), ("created_at", -1)], name="trace_complaint"
            ),
            pymongo.IndexModel([("created_at", -1)], name="trace_recent"),
            pymongo.IndexModel([("outcome", 1)], name="trace_outcome"),
        ]
