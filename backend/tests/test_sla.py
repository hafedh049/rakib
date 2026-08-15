"""SLA clock, the Tunisian working calendar, warnings, breaches and escalation."""

from datetime import UTC, date, datetime, timedelta

import pytest
import time_machine

from app.config import settings
from app.domain import calendar_tn as cal
from app.models.complaint import Assignment, Claimant, Complaint, Status
from app.models.user import Role, User
from app.services import sla_service


def at(year, month, day, hour=9, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=cal.TUNIS)


# ------------------------------------------------------------------- calendar
@pytest.mark.parametrize(
    "day,holiday",
    [
        (date(2026, 1, 1), True),    # Nouvel An
        (date(2026, 1, 14), True),   # Fete de la Revolution
        (date(2026, 3, 20), True),   # Independance (also Aid el-Fitr in 2026)
        (date(2026, 7, 25), True),   # Fete de la Republique
        (date(2026, 8, 13), True),   # Fete de la Femme
        (date(2026, 9, 16), False),
    ],
)
def test_public_holidays(day, holiday):
    assert cal.is_public_holiday(day) is holiday


def test_islamic_holidays_come_from_the_table():
    assert cal.is_public_holiday(date(2026, 5, 27)) is True   # Aid el-Idha
    assert cal.is_public_holiday(date(2026, 5, 30)) is False


def test_unknown_year_degrades_to_fixed_holidays_only():
    """Lunar dates are announced by observation; an unseen year still works."""
    assert cal.is_public_holiday(date(2035, 1, 1)) is True
    assert cal.is_public_holiday(date(2035, 5, 27)) is False


def test_weekend_is_not_a_business_day():
    assert cal.is_business_day(date(2026, 9, 12)) is False  # Saturday
    assert cal.is_business_day(date(2026, 9, 13)) is False  # Sunday
    assert cal.is_business_day(date(2026, 9, 14)) is True   # Monday


def test_summer_uses_seance_unique():
    assert cal.business_hours(date(2026, 7, 15)) == cal.SUMMER_HOURS
    assert cal.business_hours(date(2026, 9, 15)) == cal.ORDINARY_HOURS


def test_ramadan_shortens_the_day():
    assert cal.is_ramadan(date(2026, 3, 1)) is True
    assert cal.business_hours(date(2026, 3, 2)) == cal.RAMADAN_HOURS


def test_holidays_have_no_working_hours():
    assert cal.business_hours(date(2026, 1, 1)) is None
    assert cal.working_seconds_in_day(date(2026, 1, 1)) == 0.0


# -------------------------------------------------------- business-hours maths
def test_adding_hours_inside_one_working_day():
    assert cal.add_business_hours(at(2026, 9, 14, 9), 4) == at(2026, 9, 14, 13)


def test_evening_complaint_starts_the_clock_next_morning():
    """Filed at 22:00 Monday, 2h of SLA expires at 10:00 Tuesday."""
    assert cal.add_business_hours(at(2026, 9, 14, 22), 2) == at(2026, 9, 15, 10)


def test_clock_rolls_over_the_weekend():
    """Friday 16:00 + 4h lands Monday morning, not Saturday."""
    result = cal.add_business_hours(at(2026, 9, 18, 16), 4)
    assert result.date() == date(2026, 9, 21)  # Monday
    assert result.hour == 11


def test_clock_skips_a_public_holiday():
    # 2026-01-13 is a Tuesday; the 14th is a holiday.
    result = cal.add_business_hours(at(2026, 1, 13, 16), 3)
    assert result.date() == date(2026, 1, 15)


def test_business_seconds_between_ignores_closed_time():
    elapsed = cal.business_seconds_between(at(2026, 9, 18, 16), at(2026, 9, 21, 9))
    assert elapsed == pytest.approx(2 * 3600, abs=60)  # 1h Friday + 1h Monday


def test_business_seconds_of_a_closed_window_is_zero():
    assert cal.business_seconds_between(at(2026, 9, 19, 9), at(2026, 9, 20, 17)) == 0.0


# ------------------------------------------------------------------ sla clock
def test_wall_clock_mode_is_literal(monkeypatch):
    monkeypatch.setattr(settings, "sla_business_hours", False)
    start = at(2026, 9, 18, 16)
    assert sla_service.due_at(start, 4) == start + timedelta(hours=4)


def test_business_hours_mode_uses_the_calendar(monkeypatch):
    monkeypatch.setattr(settings, "sla_business_hours", True)
    result = sla_service.due_at(at(2026, 9, 18, 16), 4)
    assert result.date() == date(2026, 9, 21)


@pytest.mark.parametrize(
    "priority,hours", [(1, 4), (2, 24), (3, 72), (4, 168), (None, 72)]
)
def test_hours_per_priority(priority, hours):
    assert sla_service.hours_for_priority(priority) == hours


# ------------------------------------------------------------------- sweeping
async def make_open_complaint(
    ref: str, created_at: datetime, hours: int = 4, priority: int = 1,
    department_id=None, agent_id=None,
) -> Complaint:
    complaint = Complaint(
        ref=ref,
        claimant=Claimant(full_name="Fatma", email="fatma@example.tn"),
        subject="Agios", body="ma agios est trop elevee ce mois ci",
        status=Status.ASSIGNED,
        created_at=created_at, updated_at=created_at,
        assignment=Assignment(department_id=department_id, agent_id=agent_id),
    )
    complaint.analysis.priority = priority
    complaint.sla.hours = hours
    complaint.sla.due_at = created_at + timedelta(hours=hours)
    await complaint.insert()
    return complaint


async def test_sweep_warns_at_eighty_percent(monkeypatch):
    monkeypatch.setattr(settings, "sla_business_hours", False)
    now = datetime.now(UTC)
    await make_open_complaint("REC-2026-10001", now - timedelta(hours=3.4), hours=4)

    result = await sla_service.sweep(now)
    assert result["warned"] == 1
    assert result["breached"] == 0

    complaint = await Complaint.find_one(Complaint.ref == "REC-2026-10001")
    assert complaint.sla.warned is True
    assert complaint.sla.breached is False


async def test_sweep_does_not_warn_twice(monkeypatch):
    monkeypatch.setattr(settings, "sla_business_hours", False)
    now = datetime.now(UTC)
    await make_open_complaint("REC-2026-10002", now - timedelta(hours=3.4), hours=4)

    assert (await sla_service.sweep(now))["warned"] == 1
    assert (await sla_service.sweep(now))["warned"] == 0


async def test_sweep_marks_a_breach(monkeypatch):
    monkeypatch.setattr(settings, "sla_business_hours", False)
    now = datetime.now(UTC)
    await make_open_complaint("REC-2026-10003", now - timedelta(hours=9), hours=4)

    result = await sla_service.sweep(now)
    assert result["breached"] == 1

    complaint = await Complaint.find_one(Complaint.ref == "REC-2026-10003")
    assert complaint.sla.breached is True
    assert any(e.action == "sla.breached" for e in complaint.timeline)


async def test_resolved_complaints_are_not_swept(monkeypatch):
    monkeypatch.setattr(settings, "sla_business_hours", False)
    now = datetime.now(UTC)
    complaint = await make_open_complaint(
        "REC-2026-10004", now - timedelta(hours=99), hours=4
    )
    complaint.status = Status.RESOLVED
    await complaint.save()

    result = await sla_service.sweep(now)
    assert result["breached"] == 0


async def test_breach_escalates_to_the_department_contact(monkeypatch, departments):
    monkeypatch.setattr(settings, "sla_business_hours", False)
    supervisor = User(
        email="chef@rakib.tn", password_hash="x", full_name="Chef",
        role=Role.SUPERVISOR,
    )
    await supervisor.insert()
    department = departments["RELATION_CLIENT"]
    department.escalation_to = supervisor.id
    await department.save()

    now = datetime.now(UTC)
    await make_open_complaint(
        "REC-2026-10005", now - timedelta(hours=9), hours=4,
        department_id=department.id,
    )

    result = await sla_service.sweep(now)
    assert result["escalated"] == 1

    complaint = await Complaint.find_one(Complaint.ref == "REC-2026-10005")
    assert complaint.sla.escalation_level == 1


async def test_breach_without_an_escalation_contact_still_breaches(
    monkeypatch, departments
):
    monkeypatch.setattr(settings, "sla_business_hours", False)
    now = datetime.now(UTC)
    await make_open_complaint(
        "REC-2026-10006", now - timedelta(hours=9), hours=4,
        department_id=departments["RELATION_CLIENT"].id,
    )
    result = await sla_service.sweep(now)
    assert result["breached"] == 1
    assert result["escalated"] == 0


async def test_consumed_ratio_tracks_elapsed_budget(monkeypatch):
    monkeypatch.setattr(settings, "sla_business_hours", False)
    now = datetime.now(UTC)
    complaint = await make_open_complaint(
        "REC-2026-10007", now - timedelta(hours=2), hours=4
    )
    assert sla_service.consumed_ratio(complaint, now) == pytest.approx(0.5, abs=0.01)


async def test_sweep_publishes_breach_and_escalation_events(
    monkeypatch, departments
):
    from app.events.types import EventName

    published: list[EventName] = []

    async def capture(event, payload):
        published.append(event)
        return "0-1"

    monkeypatch.setattr(settings, "sla_business_hours", False)
    monkeypatch.setattr("app.services.sla_service.publish", capture)

    supervisor = User(
        email="chef2@rakib.tn", password_hash="x", full_name="Chef2",
        role=Role.SUPERVISOR,
    )
    await supervisor.insert()
    department = departments["MONETIQUE"]
    department.escalation_to = supervisor.id
    await department.save()

    now = datetime.now(UTC)
    await make_open_complaint(
        "REC-2026-10008", now - timedelta(hours=9), hours=4,
        department_id=department.id,
    )
    await sla_service.sweep(now)

    assert EventName.SLA_BREACHED in published
    assert EventName.ESCALATED in published


@time_machine.travel(datetime(2026, 9, 21, 10, 0, tzinfo=UTC))
async def test_sweep_with_frozen_time(monkeypatch):
    """Frozen clock: the sweep must use it rather than the wall clock."""
    monkeypatch.setattr(settings, "sla_business_hours", False)
    await make_open_complaint(
        "REC-2026-10009", datetime(2026, 9, 21, 1, 0, tzinfo=UTC), hours=4
    )
    result = await sla_service.sweep()
    assert result["breached"] == 1


# ------------------------------------------------------- Article 8: legal ceiling
def _complaint_at(moment, category=None):
    from app.models.complaint import Claimant, Complaint

    complaint = Complaint(
        ref="REC-2026-90001",
        claimant=Claimant(full_name="Test"),
        subject="s",
        body="b",
        created_at=moment,
    )
    complaint.analysis.category = category
    return complaint


def test_legal_deadline_defaults_to_the_full_ceiling_when_uncategorised():
    """We may not invent a shorter deadline for something we have not understood."""
    from app.domain.bct import DELAI_LEGAL_JOURS_OUVRABLES
    from app.services.complaint_service import apply_legal_deadline

    complaint = _complaint_at(datetime(2026, 8, 13, 10, 0, tzinfo=UTC))
    apply_legal_deadline(complaint)
    assert complaint.sla.legal_days == DELAI_LEGAL_JOURS_OUVRABLES == 15


def test_legal_deadline_is_differentiated_by_category():
    """Article 8 allows a delay reflecting "la nature et la complexite"."""
    from app.services.complaint_service import apply_legal_deadline

    fraud = _complaint_at(
        datetime(2026, 8, 13, 10, 0, tzinfo=UTC), "FRAUDE_OPERATION_NON_AUTORISEE"
    )
    credit = _complaint_at(
        datetime(2026, 8, 13, 10, 0, tzinfo=UTC), "CREDIT_FINANCEMENT"
    )
    apply_legal_deadline(fraud)
    apply_legal_deadline(credit)

    assert fraud.sla.legal_days == 2
    assert credit.sla.legal_days == 10
    assert fraud.sla.legal_due_at < credit.sla.legal_due_at


def test_no_internal_target_may_outlive_the_legal_ceiling():
    """A bank may be faster than the regulation; it may never be slower."""
    from app.services.complaint_service import apply_legal_deadline

    complaint = _complaint_at(
        datetime(2026, 8, 13, 10, 0, tzinfo=UTC), "FRAUDE_OPERATION_NON_AUTORISEE"
    )
    complaint.sla.due_at = datetime(2026, 12, 1, tzinfo=UTC)
    apply_legal_deadline(complaint)
    assert complaint.sla.due_at == complaint.sla.legal_due_at


def test_the_clock_counts_working_days_not_calendar_days():
    """Two jours ouvrables from a Thursday is Monday, not Saturday."""
    from app.domain.calendar_tn import add_business_days

    thursday = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    assert add_business_days(thursday, 2).date().weekday() == 0  # Monday
    # Fifteen working days spans well over three calendar weeks.
    assert (add_business_days(thursday, 15).date() - thursday.date()).days >= 20


def test_the_clock_starts_at_the_acknowledgement_not_at_receipt():
    """Article 8 counts from the accuse de reception."""
    from app.services.complaint_service import apply_legal_deadline

    complaint = _complaint_at(datetime(2026, 8, 3, 10, 0, tzinfo=UTC), "CARTE_BANCAIRE")
    apply_legal_deadline(complaint)
    from_receipt = complaint.sla.legal_due_at

    complaint.reglementaire.accuse_reception_at = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    apply_legal_deadline(complaint)
    assert complaint.sla.legal_due_at > from_receipt
