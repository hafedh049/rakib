"""Keyword-derived subcategories.

Deliberately NOT a second classifier: at roughly 80 samples per subclass a
model would be noise, while a keyword map is exact, explainable and free
(locked design decision for spec 3.1's `subcategory` field).
"""

from app.domain.taxonomy import Category
from app.intelligence.rules.engine import find_terms

SUBCATEGORY_TERMS: dict[str, dict[str, list[str]]] = {
    Category.FACTURATION: {
        "double_prelevement": ["deux fois", "double", "doublon", "preleve deux",
                               "مرتين", "zouz marrat"],
        "hors_forfait": ["hors forfait", "depassement", "consommation excessive",
                         "خارج الاشتراك"],
        "montant_conteste": ["montant", "eleve", "cher", "exorbitant", "anormal",
                             "غالي", "مبلغ", "ghali"],
        "frais_inattendus": ["frais", "mise en service", "penalite", "majoration",
                             "معاليم"],
    },
    Category.PAIEMENT_RECHARGE: {
        "recharge_non_creditee": ["non creditee", "pas credite", "solde",
                                  "ma wsalnich", "ما وصلش"],
        "paiement_echoue": ["echec", "echoue", "refuse", "erreur de paiement",
                            "فشل", "ma khdemch"],
        "double_debit": ["debite deux", "deux fois", "double debit", "مرتين"],
    },
    Category.RESEAU_MOBILE: {
        "absence_signal": ["aucun reseau", "pas de reseau", "sans reseau", "coupure totale",
                           "ما فماش شبكه", "famech reseau"],
        "debit_faible": ["lent", "lenteur", "debit", "faible", "بطيء", "batee"],
        "appels_coupes": ["appel coupe", "coupe", "raccroche", "تنقطع"],
        "couverture": ["couverture", "zone", "quartier", "تغطيه"],
    },
    Category.INTERNET_FIXE: {
        "panne_totale": ["panne", "coupee", "aucune connexion", "hors service",
                         "عطب", "منقطع"],
        "debit_faible": ["debit", "lent", "mbps", "بطيء"],
        "deconnexions": ["deconnexion", "se coupe", "instable", "تقطع"],
        "installation": ["installation", "raccordement", "nouvelle ligne", "تركيب"],
    },
    Category.INTERVENTION_TECHNIQUE: {
        "rdv_manque": ["rendez-vous", "personne n'est venu", "non venu", "ما جاش"],
        "delai_depasse": ["delai", "toujours pas", "depuis", "تاخير"],
        "ligne_endommagee": ["cable", "sectionne", "travaux", "كابل"],
    },
    Category.OFFRES_ABONNEMENT: {
        "promotion_non_appliquee": ["promotion", "remise", "offre speciale", "عرض"],
        "changement_forfait": ["changement", "migrer", "upgrade", "forfait superieur"],
        "engagement": ["engagement", "duree", "contrat", "التزام"],
    },
    Category.RESILIATION_PORTABILITE: {
        "resiliation_sans_suite": ["resiliation", "demande deposee", "sans suite", "فسخ"],
        "portabilite_bloquee": ["portabilite", "bloquee", "transfert", "نقل الرقم"],
    },
    Category.SERVICE_CLIENT_AGENCE: {
        "attente_agence": ["attente", "file", "guichet", "queue", "انتظار"],
        "comportement_agent": ["comportement", "desagreable", "impoli", "معامله"],
        "injoignable": ["injoignable", "personne ne repond", "ne repond pas", "ما يجاوبش"],
    },
    Category.EQUIPEMENT: {
        "materiel_defectueux": ["defectueux", "ne s'allume pas", "en panne", "معطب"],
        "sim": ["sim", "puce", "شريحه"],
        "decodeur": ["decodeur", "tv", "redemarre"],
    },
    Category.ROAMING_INTERNATIONAL: {
        "frais_roaming": ["roaming", "itinerance", "sejour", "etranger", "تجوال"],
        "appels_internationaux": ["international", "vers la france", "surtaxe"],
    },
    Category.APPLICATION_MOBILE: {
        "connexion_impossible": ["connexion", "login", "identifiants", "mot de passe",
                                 "تسجيل الدخول"],
        "donnees_incorrectes": ["solde", "incorrect", "faux", "affiche"],
        "plantage": ["plante", "crash", "ferme", "bug", "tetsakker"],
    },
}


def detect_subcategory(category: str | None, text: str) -> str | None:
    """Best-matching subcategory for a category, or None when nothing fires."""
    if category is None:
        return None
    candidates = SUBCATEGORY_TERMS.get(category)
    if not candidates:
        return None

    best: tuple[str, int] | None = None
    for subcategory, terms in candidates.items():
        score = len(find_terms(text, terms))
        if score and (best is None or score > best[1]):
            best = (subcategory, score)
    return best[0] if best else None
