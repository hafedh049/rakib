from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import NotFound, ValidationError
from app.deps import AdminUser, SupervisorUser
from app.intelligence.rules.engine import RuleContext, evaluate
from app.intelligence.rules.subcategory import detect_subcategory
from app.intelligence.text import language as lid
from app.intelligence.text.normalize import normalize
from app.models.rule import Rule, RuleKind
from app.services.rules_service import load_rule_specs

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    code: str
    label: str
    kind: RuleKind
    config: dict[str, Any]
    weight: int
    active: bool
    order: int
    builtin: bool


class RulePatch(BaseModel):
    label: str | None = None
    weight: int | None = Field(default=None, ge=-100, le=100)
    active: bool | None = None
    order: int | None = Field(default=None, ge=0, le=1000)
    config: dict[str, Any] | None = None


class SimulateRequest(BaseModel):
    """Arbitrary text plus the context a real complaint would carry."""

    subject: str = ""
    body: str = Field(min_length=1, max_length=10_000)
    category: str | None = None
    channel: str = "web"
    claimant_is_vip: bool = False
    prior_count_30d: int = Field(default=0, ge=0, le=100)
    prior_open: int = Field(default=0, ge=0, le=100)
    attachment_count: int = Field(default=0, ge=0, le=20)


class SimulatedHit(BaseModel):
    code: str
    label: str
    weight: int
    matched: list[str]


class SimulateResponse(BaseModel):
    priority: int
    priority_score: int
    urgency_score: float
    sentiment: str
    sentiment_score: float
    language: str
    language_source: str
    subcategory: str | None
    normalized_text: str
    transliterated: str
    hits: list[SimulatedHit]
    features: dict[str, Any]


@router.get("", response_model=list[RuleOut])
async def list_rules(_: SupervisorUser) -> list[Rule]:
    return await Rule.find_all().sort("order").to_list()


@router.patch("/{rule_id}", response_model=RuleOut)
async def patch_rule(
    rule_id: PydanticObjectId, payload: RulePatch, _: AdminUser
) -> Rule:
    rule = await Rule.get(rule_id)
    if rule is None:
        raise NotFound("Regle introuvable")

    updates = payload.model_dump(exclude_unset=True)
    if "config" in updates and updates["config"] is not None:
        _validate_config(str(rule.kind), updates["config"])
    for field, value in updates.items():
        setattr(rule, field, value)
    rule.updated_at = datetime.now(UTC)
    await rule.save()
    return rule


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(payload: SimulateRequest, _: SupervisorUser) -> SimulateResponse:
    """Run the rules engine on arbitrary text. Nothing is persisted.

    This is the tuning surface: paste a complaint, see exactly which rules fire
    and on which tokens, adjust a weight, run it again.
    """
    normalized = normalize(
        payload.subject, payload.body, has_attachment=payload.attachment_count > 0
    )
    detected = lid.detect(normalized)
    context = RuleContext(
        text=normalized.text,
        transliterated=normalized.transliterated,
        features=normalized.features,
        language=detected.code,
        category=payload.category,
        channel=payload.channel,
        claimant_is_vip=payload.claimant_is_vip,
        prior_count_30d=payload.prior_count_30d,
        prior_open=payload.prior_open,
        attachment_count=payload.attachment_count,
    )
    result = evaluate(await load_rule_specs(active_only=False), context)

    return SimulateResponse(
        priority=result.priority,
        priority_score=result.priority_score,
        urgency_score=result.urgency_score,
        sentiment=result.sentiment,
        sentiment_score=result.sentiment_score,
        language=detected.code,
        language_source=detected.source,
        subcategory=detect_subcategory(payload.category, normalized.indexable),
        normalized_text=normalized.text,
        transliterated=normalized.transliterated,
        hits=[
            SimulatedHit(
                code=hit.code, label=hit.label, weight=hit.weight, matched=hit.matched
            )
            for hit in result.hits
        ],
        features=vars(normalized.features),
    )


def _validate_config(kind: str, config: dict[str, Any]) -> None:
    required = {
        "lexicon": ["terms"],
        "regex": ["pattern"],
        "field": ["path", "op"],
        "history": ["source"],
        "category_weight": ["map"],
    }.get(kind, [])
    missing = [key for key in required if key not in config]
    if missing:
        raise ValidationError(
            f"Configuration incomplete pour une regle '{kind}': {', '.join(missing)}"
        )
    if kind == "regex":
        import re

        try:
            re.compile(config["pattern"])
        except re.error as exc:
            raise ValidationError(f"Expression reguliere invalide: {exc}") from exc
