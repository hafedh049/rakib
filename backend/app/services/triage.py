"""Engine selection and the process-wide engine handle.

Selection happens once at startup (spec 4.1). Whatever is configured, the system
must boot: an engine that cannot load its artifacts degrades to rules rather
than raising, and `ml_artifacts/` being empty is a supported state, not an error.
"""

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.engines.rules_only import RulesOnlyTriageEngine
from app.intelligence.ports import EngineHealth, TriageEngine
from app.services.rules_service import load_rule_specs

log = get_logger(__name__)

_engine: TriageEngine | None = None


def select_engine() -> TriageEngine:
    """Build the engine for the configured backend.

    Phases 5 and 9 add MLTriageEngine and the optional LLM adapter here; until
    then every backend resolves to rules, which is the honest answer.
    """
    global _engine
    backend = settings.triage_backend
    if backend != "rules":
        log.warning(
            "triage.backend_unavailable", requested=backend, using="rules",
            reason="classifier not built yet (phase 5)",
        )
    _engine = RulesOnlyTriageEngine()
    return _engine


def get_engine() -> TriageEngine:
    return _engine or select_engine()


async def refresh_rules() -> int:
    """Reload rules from Mongo into the live engine.

    Called at startup and after any admin edit, so a weight change takes effect
    without a restart.
    """
    engine = get_engine()
    specs = await load_rule_specs(active_only=True)
    setter = getattr(engine, "set_rules", None)
    if setter is not None:
        setter(specs)
    return len(specs)


def health() -> EngineHealth:
    return get_engine().health()
