"""The seeded rule set.

Weights are calibrated against the buckets in spec 5.4:

    >= 70  priority 1 (critique)
    >= 45  priority 2 (haute)
    >= 20  priority 3 (normale)
    else   priority 4 (basse)

So a plain billing complaint lands at P3, one that mentions a lawyer or a repeat
caller reaches P2, and a VIP threatening legal action after three complaints in
a month reaches P1. Every weight is editable from /admin/rules — these are the
starting point, not the truth.
"""

from typing import Any

from app.domain.taxonomy import Category
from app.intelligence.rules.lexicons import (
    CHURN_AR,
    CHURN_FR,
    CHURN_TN,
    LEGAL_AR,
    LEGAL_FR,
    PROFANITY,
    URGENCY_AR,
    URGENCY_FR,
    URGENCY_TN,
)

#: Collective-outage wording. Many claimants describing one incident is an
#: incident cluster, and the first report of it should be escalated fast.
OUTAGE_COLLECTIVE = [
    "tout le quartier", "toute la rue", "tous les voisins", "tout l'immeuble",
    "toute la zone", "toute la region", "plusieurs clients", "tout le monde",
    "الحي الكل", "الجيران الكل", "كامل المنطقه", "الكل",
    "el 7ouma kamla", "el jiran", "ga3", "lkol",
]

DEFAULT_RULES: list[dict[str, Any]] = [
    # ------------------------------------------------------------------ urgency
    {
        "code": "URGENCY_LEXICON_FR", "label": "Vocabulaire d'urgence (FR)",
        "kind": "lexicon", "weight": 15, "order": 10,
        "config": {"terms": URGENCY_FR, "lang": "fr", "cap": 2},
    },
    {
        "code": "URGENCY_LEXICON_AR", "label": "Vocabulaire d'urgence (AR)",
        "kind": "lexicon", "weight": 15, "order": 11,
        "config": {"terms": URGENCY_AR, "lang": "ar", "cap": 2},
    },
    {
        "code": "URGENCY_LEXICON_TN", "label": "Vocabulaire d'urgence (derja)",
        "kind": "lexicon", "weight": 15, "order": 12,
        "config": {"terms": URGENCY_TN, "lang": "ar-tn", "cap": 2},
    },
    # -------------------------------------------------------------------- legal
    {
        "code": "LEGAL_LEXICON_FR", "label": "Menace juridique (FR)",
        "kind": "lexicon", "weight": 30, "order": 20,
        "config": {"terms": LEGAL_FR, "lang": "fr", "cap": 1},
    },
    {
        "code": "LEGAL_LEXICON_AR", "label": "Menace juridique (AR)",
        "kind": "lexicon", "weight": 30, "order": 21,
        "config": {"terms": LEGAL_AR, "lang": "ar", "cap": 1},
    },
    # -------------------------------------------------------------------- churn
    {
        "code": "CHURN_LEXICON_FR", "label": "Risque de resiliation (FR)",
        "kind": "lexicon", "weight": 20, "order": 30,
        "config": {"terms": CHURN_FR, "lang": "fr", "cap": 1},
    },
    {
        "code": "CHURN_LEXICON_AR", "label": "Risque de resiliation (AR/derja)",
        "kind": "lexicon", "weight": 20, "order": 31,
        "config": {"terms": CHURN_AR + CHURN_TN, "lang": "ar", "cap": 1},
    },
    # ---------------------------------------------------------------- incidents
    {
        "code": "OUTAGE_COLLECTIVE", "label": "Panne collective signalee",
        "kind": "lexicon", "weight": 20, "order": 40,
        "config": {"terms": OUTAGE_COLLECTIVE, "cap": 1},
    },
    {
        "code": "PROFANITY", "label": "Propos agressifs",
        "kind": "lexicon", "weight": 10, "order": 41,
        "config": {"terms": PROFANITY, "cap": 1},
    },
    # ------------------------------------------------------------------- client
    {
        "code": "VIP_CLAIMANT", "label": "Client VIP / compte entreprise",
        "kind": "field", "weight": 25, "order": 50,
        "config": {"path": "claimant_is_vip", "op": "eq", "value": True},
    },
    {
        "code": "REPEAT_CLAIMANT_30D", "label": "Reclamations repetees (30 jours)",
        "kind": "history", "weight": 20, "order": 51,
        "config": {"source": "prior_count_30d", "min_count": 3, "window_days": 30},
    },
    {
        "code": "MULTIPLE_OPEN", "label": "Plusieurs dossiers ouverts",
        "kind": "history", "weight": 10, "order": 52,
        "config": {"source": "prior_open", "min_count": 2},
    },
    # -------------------------------------------------------------------- style
    {
        "code": "SHOUTING", "label": "Message en majuscules",
        "kind": "field", "weight": 8, "order": 60,
        "config": {"path": "uppercase_ratio", "op": "gte", "value": 0.4},
    },
    {
        "code": "EXCLAMATION_STORM", "label": "Ponctuation excessive",
        "kind": "field", "weight": 5, "order": 61,
        "config": {"path": "exclamation_count", "op": "gte", "value": 3},
    },
    {
        "code": "HAS_ATTACHMENT", "label": "Piece jointe fournie",
        "kind": "field", "weight": 5, "order": 62,
        "config": {"path": "attachment_count", "op": "gte", "value": 1},
    },
    {
        "code": "VERY_SHORT", "label": "Message tres court (peu d'information)",
        "kind": "length", "weight": -8, "order": 63,
        "config": {"max": 60},
    },
    {
        "code": "DETAILED_REPORT", "label": "Description detaillee",
        "kind": "length", "weight": 5, "order": 64,
        "config": {"min": 800},
    },
    # ------------------------------------------------------------------ patterns
    {
        "code": "INVOICE_REFERENCE", "label": "Reference de facture citee",
        "kind": "regex", "weight": 5, "order": 70,
        "config": {"pattern": r"\b(?:facture|fact|inv)[\s.:#-]*\d{4,}\b", "flags": "i"},
    },
    {
        "code": "AMOUNT_IN_DINARS", "label": "Montant conteste en dinars",
        "kind": "regex", "weight": 8, "order": 71,
        "config": {
            "pattern": r"\b\d{2,5}(?:[.,]\d{1,3})?\s*(?:dinars?|dt|tnd|دينار)\b",
            "flags": "i",
        },
    },
    {
        "code": "DURATION_WEEKS", "label": "Probleme persistant (semaines/mois)",
        "kind": "regex", "weight": 12, "order": 72,
        "config": {
            "pattern": r"\b(?:depuis|من|men)\s+(?:\d+\s+)?(?:semaines?|mois|"
                       r"اسابيع|اشهر|semaine|chhar|jom3a)\b",
            "flags": "i",
        },
    },
    # ------------------------------------------------------------------ category
    {
        "code": "CATEGORY_WEIGHTS", "label": "Ponderation par categorie",
        "kind": "category_weight", "weight": 1, "order": 80,
        "config": {
            "map": {
                Category.FACTURATION: 10,
                Category.PAIEMENT_RECHARGE: 10,
                Category.INTERNET_FIXE: 8,
                Category.RESEAU_MOBILE: 8,
                Category.INTERVENTION_TECHNIQUE: 8,
                Category.RESILIATION_PORTABILITE: 6,
                Category.ROAMING_INTERNATIONAL: 6,
                Category.SERVICE_CLIENT_AGENCE: 4,
                Category.OFFRES_ABONNEMENT: 4,
                Category.EQUIPEMENT: 4,
                Category.APPLICATION_MOBILE: 2,
            }
        },
    },
]
