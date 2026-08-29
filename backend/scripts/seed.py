"""Demo seed: departments, staff, and a month of realistic complaints.

    python -m scripts.seed            # idempotent-ish: skips if complaints exist
    python -m scripts.seed --force    # wipe complaints/users and reseed

Staff, claimants and complaint bodies live in scripts/seed_data.py so this
file stays about the seeding logic.
"""

import argparse
import asyncio
import random
from datetime import UTC, datetime, timedelta

from app import db
from app.config import settings
from app.core.security import hash_password
from app.models.complaint import (
    Channel,
    Claimant,
    Complaint,
    Status,
)
from app.models.counter import Counter, next_complaint_ref
from app.models.department import Department
from app.models.user import Role, User
from app.services.seed_service import seed_departments
from scripts.seed_data import CLAIMANTS, COMPLAINTS, STAFF

SEED = 20260908
DEMO_PASSWORD = "Rakib2026!"


STATUS_MIX = (
    [Status.NEW] * 8
    + [Status.TRIAGED] * 4
    + [Status.ASSIGNED] * 10
    + [Status.IN_PROGRESS] * 12
    + [Status.PENDING_CLAIMANT] * 4
    + [Status.RESOLVED] * 16
    + [Status.CLOSED] * 5
    + [Status.REJECTED] * 1
)

CHANNEL_MIX = [Channel.WEB] * 7 + [Channel.PHONE] * 2 + [Channel.AGENCE] * 2 + [Channel.EMAIL]


async def main(force: bool = False, count: int = 60, triage: bool = True) -> None:
    random.seed(SEED)
    await db.init_db()

    if force:
        await Complaint.find_all().delete()
        await User.find_all().delete()
        await Counter.find_all().delete()
        print("wiped complaints, users, counters")

    created_departments = await seed_departments()
    departments = {d.code: d for d in await Department.find_all().to_list()}
    print(f"departments: {len(departments)} ({created_departments} created)")

    if await User.find_one(User.email == STAFF[0][0]) is None:
        for email, name, role, dept_code, skills in STAFF:
            await User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=name,
                role=role,
                department_id=departments[dept_code].id if dept_code else None,
                skills=skills,
                max_concurrent=15,
                last_active_at=datetime.now(UTC) - timedelta(hours=random.randint(0, 40)),
            ).insert()
        print(f"staff: {len(STAFF)} created (password: {DEMO_PASSWORD})")

    existing = await Complaint.find_all().count()
    if existing and not force:
        print(f"complaints: {existing} already present — skipping (use --force)")
        await db.close_db()
        return

    agents = await User.find(User.role == Role.AGENT).to_list()
    agents_by_department: dict[str, list[User]] = {}
    for agent in agents:
        for code, department in departments.items():
            if agent.department_id == department.id:
                agents_by_department.setdefault(code, []).append(agent)

    now = datetime.now(UTC)
    for index in range(count):
        category, subject, body = COMPLAINTS[index % len(COMPLAINTS)]
        name, email, phone, is_vip = CLAIMANTS[index % len(CLAIMANTS)]
        status = STATUS_MIX[index % len(STATUS_MIX)]

        # Age follows the status. Spreading every complaint evenly over 30 days
        # made the board read as if nothing ever moved: open work is recent,
        # closed work is older.
        if status in (Status.RESOLVED, Status.CLOSED, Status.REJECTED):
            age_hours = random.randint(48, 30 * 24)
        elif status in (Status.NEW, Status.TRIAGED):
            age_hours = random.randint(0, 6)
        else:
            age_hours = random.randint(2, 60)
        created_at = now - timedelta(hours=age_hours)

        complaint = Complaint(
            ref=await next_complaint_ref(created_at),
            channel=random.choice(CHANNEL_MIX),
            claimant=Claimant(
                full_name=name, email=email, phone=phone, is_vip=is_vip
            ),
            subject=subject,
            body=body,
            status=status,
            created_at=created_at,
            updated_at=created_at,
        )
        complaint.log("complaint.created", channel=str(complaint.channel))
        await complaint.insert()

    print(f"complaints: {count} created")

    # Run the pipeline over the seeded rows. Without this the demo opens on 60
    # complaints that all say "analyse en attente" — no categories, no routing,
    # nothing to filter on.
    if triage:
        from app.services import triage_service


        done = 0
        for complaint in await Complaint.find_all().to_list():
            await triage_service.triage_complaint(complaint)
            done += 1
            if done % 20 == 0:
                print(f"  triaged {done}/{count}")
        print(f"triage: {done} complaints analysed")

    print(f"\nSign in at {settings.frontend_url} — admin@rakib.tn / {DEMO_PASSWORD}")
    await db.close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Rakib demo dataset")
    parser.add_argument("--force", action="store_true", help="wipe and reseed")
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument(
        "--no-triage", dest="triage", action="store_false",
        help="skip running the pipeline over the seeded complaints",
    )
    asyncio.run(main(**vars(parser.parse_args())))
