"""Tunisian working calendar.

A SLA of "4 hours" that expires at 02:00 on a Sunday is a fiction. When
SLA_BUSINESS_HOURS is on, the clock only runs during hours when someone is
actually at a desk — which in Tunisia means three different schedules:

  * ordinary weeks   Mon-Fri 08:00-17:00
  * summer (Jul-Aug) "seance unique", 07:30-13:30
  * Ramadan          shortened day, 08:00-14:00

Islamic holidays move with the lunar calendar and are announced by the Mufti, so
they cannot be computed — they live in a table that an admin extends each year.
An unknown year degrades to fixed holidays only, which is wrong by a day or two
rather than catastrophically.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TUNIS = ZoneInfo("Africa/Tunis")

#: Fixed civil holidays (month, day).
FIXED_HOLIDAYS: set[tuple[int, int]] = {
    (1, 1),    # Nouvel An
    (1, 14),   # Fete de la Revolution et de la Jeunesse
    (3, 20),   # Fete de l'Independance
    (4, 9),    # Journee des Martyrs
    (5, 1),    # Fete du Travail
    (7, 25),   # Fete de la Republique
    (8, 13),   # Fete de la Femme
    (10, 15),  # Fete de l'Evacuation
}

#: Lunar holidays, per year. Announced by observation — extend as they are set.
ISLAMIC_HOLIDAYS: dict[int, list[date]] = {
    2026: [
        date(2026, 3, 20), date(2026, 3, 21), date(2026, 3, 22),  # Aid el-Fitr
        date(2026, 5, 27), date(2026, 5, 28), date(2026, 5, 29),  # Aid el-Idha
        date(2026, 6, 17),                                         # Ras el Am Hijri
        date(2026, 8, 26),                                         # Mouled
    ],
    2027: [
        date(2027, 3, 10), date(2027, 3, 11), date(2027, 3, 12),
        date(2027, 5, 17), date(2027, 5, 18), date(2027, 5, 19),
        date(2027, 6, 7),
        date(2027, 8, 15),
    ],
}

#: Approximate Ramadan windows (start, end inclusive).
RAMADAN: dict[int, tuple[date, date]] = {
    2026: (date(2026, 2, 18), date(2026, 3, 19)),
    2027: (date(2027, 2, 8), date(2027, 3, 9)),
}

ORDINARY_HOURS = (time(8, 0), time(17, 0))
SUMMER_HOURS = (time(7, 30), time(13, 30))
RAMADAN_HOURS = (time(8, 0), time(14, 0))

SUMMER_MONTHS = {7, 8}
WEEKEND = {5, 6}  # Saturday, Sunday


def is_public_holiday(day: date) -> bool:
    if (day.month, day.day) in FIXED_HOLIDAYS:
        return True
    return day in ISLAMIC_HOLIDAYS.get(day.year, [])


def is_ramadan(day: date) -> bool:
    window = RAMADAN.get(day.year)
    return bool(window and window[0] <= day <= window[1])


def is_business_day(day: date) -> bool:
    return day.weekday() not in WEEKEND and not is_public_holiday(day)


def business_hours(day: date) -> tuple[time, time] | None:
    """Working window for a day, or None when nobody is working."""
    if not is_business_day(day):
        return None
    if is_ramadan(day):
        return RAMADAN_HOURS
    if day.month in SUMMER_MONTHS:
        return SUMMER_HOURS
    return ORDINARY_HOURS


def working_seconds_in_day(day: date) -> float:
    window = business_hours(day)
    if window is None:
        return 0.0
    start, end = window
    return (
        datetime.combine(day, end) - datetime.combine(day, start)
    ).total_seconds()


def add_business_hours(start: datetime, hours: float) -> datetime:
    """Advance `start` by `hours` of working time, in Africa/Tunis.

    Returns an aware datetime in the same timezone as the input.
    """
    original_tz = start.tzinfo
    moment = start.astimezone(TUNIS)
    remaining = hours * 3600

    # A complaint filed at 22:00 starts its clock at 08:00 the next working day.
    moment = _advance_to_open(moment)

    guard = 0
    while remaining > 0:
        guard += 1
        if guard > 3650:  # ten years of days — a runaway loop, not a real SLA
            return moment.astimezone(original_tz) if original_tz else moment

        window = business_hours(moment.date())
        if window is None:
            moment = _next_day_open(moment)
            continue

        close = datetime.combine(moment.date(), window[1], tzinfo=TUNIS)
        available = (close - moment).total_seconds()
        if available <= 0:
            moment = _next_day_open(moment)
            continue

        if remaining <= available:
            moment = moment + timedelta(seconds=remaining)
            remaining = 0
        else:
            remaining -= available
            moment = _next_day_open(close)

    return moment.astimezone(original_tz) if original_tz else moment


def _advance_to_open(moment: datetime) -> datetime:
    window = business_hours(moment.date())
    if window is None:
        return _next_day_open(moment)
    open_at = datetime.combine(moment.date(), window[0], tzinfo=TUNIS)
    close_at = datetime.combine(moment.date(), window[1], tzinfo=TUNIS)
    if moment < open_at:
        return open_at
    if moment >= close_at:
        return _next_day_open(moment)
    return moment


def _next_day_open(moment: datetime) -> datetime:
    day = moment.date() + timedelta(days=1)
    for _ in range(400):
        window = business_hours(day)
        if window is not None:
            return datetime.combine(day, window[0], tzinfo=TUNIS)
        day += timedelta(days=1)
    return moment + timedelta(days=1)


def business_seconds_between(start: datetime, end: datetime) -> float:
    """Working seconds elapsed between two instants — used for the 80% warning."""
    if end <= start:
        return 0.0
    current = _advance_to_open(start.astimezone(TUNIS))
    finish = end.astimezone(TUNIS)
    total = 0.0

    guard = 0
    while current < finish and guard < 3650:
        guard += 1
        window = business_hours(current.date())
        if window is None:
            current = _next_day_open(current)
            continue
        close = datetime.combine(current.date(), window[1], tzinfo=TUNIS)
        segment_end = min(close, finish)
        total += max(0.0, (segment_end - current).total_seconds())
        current = _next_day_open(close)
    return total
