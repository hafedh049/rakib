"""First-boot seeding.

Lexicons, rules and the department catalogue live in Python (domain/) but are
seeded into Mongo on first boot; after that Mongo is the source of truth and the
admin UI edits it (spec section 9). Re-running is safe: existing rows are left
alone unless they are missing fields a newer version added.
"""

from app.core.logging import get_logger
from app.domain.taxonomy import DEPARTMENT_SEED
from app.models.department import Department

log = get_logger(__name__)


async def seed_departments() -> int:
    """Insert missing departments; refresh catalogue fields on existing ones.

    Name, description, keywords and categories come from the catalogue and are
    kept in step. `escalation_to`, `default_sla_hours` and `active` belong to
    the admin and are never touched by a redeploy.
    """
    created = refreshed = 0
    for seed in DEPARTMENT_SEED:
        existing = await Department.find_one(Department.code == seed.code)
        if existing is None:
            await Department(
                code=seed.code,
                name=seed.name,
                description=seed.description,
                keywords=list(seed.keywords),
                categories=list(seed.categories),
                default_sla_hours=seed.default_sla_hours,
            ).insert()
            created += 1
            continue

        if (
            existing.name != seed.name
            or existing.description != seed.description
            or existing.keywords != list(seed.keywords)
            or existing.categories != list(seed.categories)
        ):
            existing.name = seed.name
            existing.description = seed.description
            existing.keywords = list(seed.keywords)
            existing.categories = list(seed.categories)
            await existing.save()
            refreshed += 1

    if created or refreshed:
        log.info("seed.departments", created=created, refreshed=refreshed)
    return created
