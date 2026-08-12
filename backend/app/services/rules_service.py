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
    created = 0
    for definition in DEFAULT_RULES:
        if await Rule.find_one(Rule.code == definition["code"]):
            continue
        await Rule(**definition, builtin=True).insert()
        created += 1
    if created:
        log.info("seed.rules", created=created)
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
