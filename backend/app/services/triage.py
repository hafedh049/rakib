"""Engine selection and the process-wide engine handle.

Selection happens once at startup (spec 4.1). Both engines are deterministic and
neither loads an artifact, so there is no "model missing" state to degrade from
— the system either has a lexicon or it does not.

    lexicon  categorises by weighted terms, then applies the rule set. Default.
    rules    routes by department keywords only, leaving the category to an
             agent. The honest floor: correct, just less helpful.

The trained-model and LLM adapters were removed. The port they proved is still
here, and it is what made removing them a one-file change.
"""

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.engines.lexicon import LexiconTriageEngine
from app.intelligence.engines.rules_only import RulesOnlyTriageEngine
from app.intelligence.ports import EngineHealth, TriageEngine
from app.services.rules_service import load_rule_specs

log = get_logger(__name__)

_engine: TriageEngine | None = None


def select_engine() -> TriageEngine:
    """Build the engine for the configured backend."""
    global _engine

    backend = settings.triage_backend
    if backend == "rules":
        _engine = RulesOnlyTriageEngine()
    else:
        _engine = LexiconTriageEngine()

    log.info("triage.engine_selected", requested=backend, active=_engine.name)
    return _engine


def reload_model() -> bool:
    """No artifact to swap. Kept so the admin endpoint keeps its contract."""
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
