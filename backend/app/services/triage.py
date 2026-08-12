"""Engine selection and the process-wide engine handle.

Selection happens once at startup (spec 4.1). Whatever is configured, the system
must boot: an engine that cannot load its artifacts degrades to rules rather
than raising, and `ml_artifacts/` being empty is a supported state, not an error.
"""

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.engines.ml import MLTriageEngine
from app.intelligence.engines.rules_only import RulesOnlyTriageEngine
from app.intelligence.ports import EngineHealth, TriageEngine
from app.services.rules_service import load_rule_specs

log = get_logger(__name__)

_engine: TriageEngine | None = None


def select_engine() -> TriageEngine:
    """Build the engine for the configured backend.

    `ml` is the default and degrades to rules internally when artifacts are
    missing. `llm` needs a key; without one it falls back to `ml` rather than
    crashing, because a missing optional adapter must never stop the service.
    """
    global _engine
    backend = settings.triage_backend

    if backend == "rules":
        _engine = RulesOnlyTriageEngine()
    elif backend == "llm":
        if settings.openrouter_api_key:
            from app.intelligence.engines.llm import LLMTriageEngine

            _engine = LLMTriageEngine()
        else:
            log.error(
                "triage.llm_key_missing", using="ml",
                detail="TRIAGE_BACKEND=llm requires OPENROUTER_API_KEY",
            )
            _engine = MLTriageEngine()
    else:
        _engine = MLTriageEngine()

    log.info("triage.engine_selected", requested=backend, active=_engine.name)
    return _engine


def reload_model() -> bool:
    """Swap the in-memory model after a retrain or rollback (spec 5.8)."""
    engine = get_engine()
    reloader = getattr(engine, "reload", None)
    return bool(reloader()) if reloader else False


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
