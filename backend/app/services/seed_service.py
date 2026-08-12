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
    """Insert any department from the catalogue that Mongo does not yet have."""
    created = 0
    for seed in DEPARTMENT_SEED:
        if await Department.find_one(Department.code == seed.code):
            continue
        await Department(
            code=seed.code,
            name=seed.name,
            description=seed.description,
            keywords=list(seed.keywords),
            categories=list(seed.categories),
            default_sla_hours=seed.default_sla_hours,
        ).insert()
        created += 1
    if created:
        log.info("seed.departments", created=created)
    return created
