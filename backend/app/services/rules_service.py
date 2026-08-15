"""Rules stored in Mongo, loaded into the engine as plain specs.

Seeded from `intelligence/rules/defaults.py` on first boot; after that Mongo is
authoritative. Built-in rules are refreshed on reseed only where an admin has
not touched them, so tuning survives a redeploy.
"""

from app.core.logging import get_logger
from app.intelligence.rules.defaults import DEFAULT_RULES
from app.intelligence.rules.engine import RuleSpec
from app.models.rule import Rule

log = get_logger(__name__)


async def seed_rules() -> int:
    """Insert missing rules; refresh the wording and matching terms of existing ones.

    Weight, active and order are the admin's to own and are never overwritten —
    a redeploy must not silently undo someone's tuning. Label and config are
    catalogue data, so a corrected label or an added lexicon term does reach an
    already-seeded install.
    """
    created = refreshed = 0
    for definition in DEFAULT_RULES:
        existing = await Rule.find_one(Rule.code == definition["code"])
        if existing is None:
            # Upsert rather than insert: seeding runs from app startup and from
            # test fixtures, and a plain check-then-insert lets two callers both
            # observe "missing" and race into a duplicate-key error on rule_code.
            # $setOnInsert makes creation atomic and a no-op when it lost the race.
            result = await Rule.get_motor_collection().update_one(
                {"code": definition["code"]},
                {"$setOnInsert": Rule(**definition, builtin=True).model_dump(
                    by_alias=True, exclude={"id"}
                )},
                upsert=True,
            )
            if result.upserted_id is not None:
                created += 1
            continue

        if not existing.builtin:
            continue
        if existing.label != definition["label"] or existing.config != definition["config"]:
            existing.label = definition["label"]
            existing.config = definition["config"]
            await existing.save()
            refreshed += 1

    if created or refreshed:
        log.info("seed.rules", created=created, refreshed=refreshed)
    return created


async def load_rule_specs(active_only: bool = True) -> list[RuleSpec]:
    query = {"active": True} if active_only else {}
    rules = await Rule.find(query).sort("order").to_list()
    return [
        RuleSpec(
            code=rule.code,
            label=rule.label,
            kind=str(rule.kind),
            weight=rule.weight,
            config=rule.config,
            active=rule.active,
            order=rule.order,
        )
        for rule in rules
    ]
