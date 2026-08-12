"""Slot filling for reply templates.

Slots that cannot be resolved are NOT guessed and NOT silently blanked — they
come back in `missing_slots` so the composer can highlight them for the agent.
A draft that quietly invents a compensation amount is worse than one that asks.
"""

import re
from dataclasses import dataclass

SLOT_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass(frozen=True)
class FilledTemplate:
    text: str
    filled: dict[str, str]
    missing: list[str]


def slots_in(template: str) -> list[str]:
    seen: list[str] = []
    for match in SLOT_RE.finditer(template):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def fill(template: str, values: dict[str, str | None]) -> FilledTemplate:
    filled: dict[str, str] = {}
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = values.get(name)
        if value in (None, ""):
            if name not in missing:
                missing.append(name)
            # Left visible and obviously unfilled so it cannot be sent by accident.
            return f"[{name}]"
        filled[name] = str(value)
        return str(value)

    return FilledTemplate(
        text=SLOT_RE.sub(replace, template), filled=filled, missing=missing
    )
