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
    FRAUDE_AR,
    FRAUDE_FR,
    FRAUDE_TN,
    LEGAL_AR,
    LEGAL_FR,
    MEDIATEUR_AR,
    MEDIATEUR_FR,
    PROFANITY,
    URGENCY_AR,
    URGENCY_FR,
    URGENCY_TN,
)

#: Collective-incident wording. In a bank this is an ATM out of order for a whole
#: branch, a failed batch of salary transfers, or an outage of the mobile app —
#: many claimants describing one incident, where the first report should be
#: escalated fast because the rest are already on their way.
INCIDENT_COLLECTIF = [
    "tous les clients", "plusieurs clients", "tout le monde", "toute l'agence",
    "tous les collegues", "tous mes collegues", "toute l'entreprise",
    "tous les salaries", "personne n'arrive", "aucun client", "toutes les cartes",
    "tous les distributeurs", "l'application est down", "le service est down",
    "الحرفاء الكل", "الكل", "كل الحرفاء", "الوكاله الكل", "كل الزملاء",
    "el clients kamel", "ga3", "lkol", "el 3omal kamel",
]

DEFAULT_RULES: list[dict[str, Any]] = [
    # ------------------------------------------------------------------ urgency
    {
        "code": "URGENCY_LEXICON_FR", "label": "Vocabulaire d’urgence (FR)",
        "kind": "lexicon", "weight": 15, "order": 10,
        "config": {"terms": URGENCY_FR, "lang": "fr", "cap": 2},
    },
    {
        "code": "URGENCY_LEXICON_AR", "label": "Vocabulaire d’urgence (AR)",
        "kind": "lexicon", "weight": 15, "order": 11,
        "config": {"terms": URGENCY_AR, "lang": "ar", "cap": 2},
    },
    {
        "code": "URGENCY_LEXICON_TN", "label": "Vocabulaire d’urgence (derja)",
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
        "code": "CHURN_LEXICON_FR", "label": "Risque de résiliation (FR)",
        "kind": "lexicon", "weight": 20, "order": 30,
        "config": {"terms": CHURN_FR, "lang": "fr", "cap": 1},
    },
    {
        "code": "CHURN_LEXICON_AR", "label": "Risque de résiliation (AR/derja)",
        "kind": "lexicon", "weight": 20, "order": 31,
        "config": {"terms": CHURN_AR + CHURN_TN, "lang": "ar", "cap": 1},
    },
    # ------------------------------------------------------------------- fraude
    # The heaviest signals in the system. An unauthorised debit is money already
    # gone, and unlike a tariff dispute the bank's own delay compounds the
    # customer's loss. Weighted so that a bare fraud claim is P2 on its own, and
    # reaches P1 as soon as any single aggravating signal joins it.
    {
        "code": "FRAUDE_SUSPECTEE_FR", "label": "Fraude ou opération non autorisée (FR)",
        "kind": "lexicon", "weight": 55, "order": 5,
        "config": {"terms": FRAUDE_FR, "lang": "fr", "cap": 1},
    },
    {
        "code": "FRAUDE_SUSPECTEE_AR", "label": "Fraude ou opération non autorisée (AR)",
        "kind": "lexicon", "weight": 55, "order": 6,
        "config": {"terms": FRAUDE_AR, "lang": "ar", "cap": 1},
    },
    {
        "code": "FRAUDE_SUSPECTEE_TN", "label": "Fraude ou opération non autorisée (derja)",
        "kind": "lexicon", "weight": 55, "order": 7,
        "config": {"terms": FRAUDE_TN, "lang": "ar-tn", "cap": 1},
    },
    # ---------------------------------------------------------------- médiation
    # Naming the mediator or the central bank means the customer already judges
    # the internal path to have failed. Under the décret n°2006-1881 they must
    # come to the bank first, so this is the last exit before the file leaves us.
    {
        "code": "MEDIATEUR_BANCAIRE_FR", "label": "Recours au médiateur / BCT (FR)",
        "kind": "lexicon", "weight": 35, "order": 25,
        "config": {"terms": MEDIATEUR_FR, "lang": "fr", "cap": 1},
    },
    {
        "code": "MEDIATEUR_BANCAIRE_AR", "label": "Recours au médiateur / BCT (AR)",
        "kind": "lexicon", "weight": 35, "order": 26,
        "config": {"terms": MEDIATEUR_AR, "lang": "ar", "cap": 1},
    },
    # ---------------------------------------------------------------- incidents
    {
        "code": "INCIDENT_COLLECTIF", "label": "Incident collectif signalé",
        "kind": "lexicon", "weight": 20, "order": 40,
        "config": {"terms": INCIDENT_COLLECTIF, "cap": 1},
    },
    {
        "code": "PROFANITY", "label": "Propos agressifs",
        "kind": "lexicon", "weight": 10, "order": 41,
        "config": {"terms": PROFANITY, "cap": 1},
    },
    # ------------------------------------------------------------------- client
    {
        "code": "VIP_CLAIMANT", "label": "Client entreprise ou patrimonial",
        "kind": "field", "weight": 25, "order": 50,
        "config": {"path": "claimant_is_vip", "op": "eq", "value": True},
    },
    {
        "code": "REPEAT_CLAIMANT_30D", "label": "Réclamations répétées (30 jours)",
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
        "code": "HAS_ATTACHMENT", "label": "Pièce jointe fournie",
        "kind": "field", "weight": 5, "order": 62,
        "config": {"path": "attachment_count", "op": "gte", "value": 1},
    },
    {
        "code": "VERY_SHORT", "label": "Message très court (peu d’information)",
        "kind": "length", "weight": -8, "order": 63,
        "config": {"max": 60},
    },
    {
        "code": "DETAILED_REPORT", "label": "Description détaillée",
        "kind": "length", "weight": 5, "order": 64,
        "config": {"min": 800},
    },
    # ------------------------------------------------------------------ patterns
    {
        "code": "OPERATION_REFERENCE", "label": "Référence bancaire citée",
        "kind": "regex", "weight": 5, "order": 70,
        "config": {
            "pattern": r"\b(?:rib|iban|compte|carte|operation|transaction|"
                       r"virement|cheque|ref)[\s.:#\-n°]*\d{4,}\b",
            "flags": "i",
        },
    },
    {
        "code": "AMOUNT_IN_DINARS", "label": "Montant contesté en dinars",
        "kind": "regex", "weight": 8, "order": 71,
        "config": {
            "pattern": r"\b\d{2,6}(?:[.,]\d{1,3})?\s*(?:dinars?|dt|tnd|دينار)\b",
            "flags": "i",
        },
    },
    {
        # Fires in addition to the rule above, so any amount scores 8 and a large
        # one scores 20. Four digits is 1 000 DT — roughly a Tunisian monthly
        # salary, and the point at which a disputed debit stops being an
        # annoyance and starts being a hardship.
        "code": "MONTANT_ELEVE", "label": "Montant élevé (≥ 1 000 DT)",
        "kind": "regex", "weight": 12, "order": 73,
        "config": {
            "pattern": r"\b\d{4,6}(?:[.,]\d{1,3})?\s*(?:dinars?|dt|tnd|دينار)\b",
            "flags": "i",
        },
    },
    {
        "code": "DURATION_WEEKS", "label": "Problème persistant (semaines/mois)",
        "kind": "regex", "weight": 12, "order": 72,
        "config": {
            "pattern": r"\b(?:depuis|من|men)\s+(?:\d+\s+)?(?:semaines?|mois|"
                       r"اسابيع|اشهر|semaine|chhar|jom3a)\b",
            "flags": "i",
        },
    },
    # ------------------------------------------------------------------ category
    {
        "code": "CATEGORY_WEIGHTS", "label": "Pondération par catégorie",
        "kind": "category_weight", "weight": 1, "order": 80,
        "config": {
            "map": {
                # Ordered by how much of the customer's money is already gone
                # and how long it stays gone, not by how loudly they complain.
                Category.FRAUDE_OPERATION_NON_AUTORISEE: 15,
                Category.DAB_GAB: 12,
                Category.CARTE_BANCAIRE: 10,
                Category.VIREMENT_PRELEVEMENT: 10,
                Category.PAIEMENT_TPE_ECOMMERCE: 10,
                Category.CHEQUE_EFFET: 8,
                Category.CREDIT_FINANCEMENT: 8,
                Category.COMPTE_GESTION: 6,
                Category.OPERATIONS_INTERNATIONALES: 6,
                Category.FRAIS_COMMISSIONS: 6,
                Category.BANQUE_DIGITALE: 4,
                Category.AGENCE_QUALITE_SERVICE: 2,
            }
        },
    },
]
