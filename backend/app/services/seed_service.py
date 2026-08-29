"""First-boot seeding.

The department catalogue lives in Python (domain/taxonomy.py) but is seeded into
Mongo on first boot; after that Mongo is the source of truth and the admin screen
edits it. Re-running is safe: catalogue fields are refreshed, admin-owned ones
are left alone.
"""

from app.core.logging import get_logger
from app.domain.taxonomy import DEPARTMENT_SEED
from app.models.department import Department

log = get_logger(__name__)


async def seed_departments() -> int:
    """Insert missing departments; refresh catalogue fields on existing ones.

    Name, description, keywords and categories come from the catalogue and are
    kept in step. `active` belongs to the admin and is never touched by a
    redeploy.
    """
    created = refreshed = 0
    for seed in DEPARTMENT_SEED:
        existing = await Department.find_one(Department.code == seed.code)
        if existing is None:
            # Atomic upsert, not check-then-insert: seeding runs from startup and
            # from fixtures, and two callers can both observe "missing" and race
            # into a duplicate-key error on department_code.
            document = Department(
                code=seed.code,
                name=seed.name,
                description=seed.description,
                keywords=list(seed.keywords),
                categories=list(seed.categories),
            ).model_dump(by_alias=True, exclude={"id"})
            result = await Department.get_motor_collection().update_one(
                {"code": seed.code}, {"$setOnInsert": document}, upsert=True
            )
            if result.upserted_id is not None:
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
