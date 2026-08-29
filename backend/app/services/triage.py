"""The process-wide engine handle.

One engine, chosen at import: the lexicon. The port in `intelligence/ports.py`
still exists, and it is what made replacing the categoriser a one-file change
when the constraints changed.
"""

from app.core.logging import get_logger
from app.intelligence.engines.lexicon import LexiconTriageEngine
from app.intelligence.ports import EngineHealth, TriageEngine

log = get_logger(__name__)

_engine: TriageEngine | None = None


def select_engine() -> TriageEngine:
    global _engine
    _engine = LexiconTriageEngine()
    log.info("triage.engine_selected", active=_engine.name)
    return _engine


def get_engine() -> TriageEngine:
    return _engine or select_engine()


def engine_health() -> EngineHealth:
    return get_engine().health()
