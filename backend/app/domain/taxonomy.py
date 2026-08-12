"""The complaint taxonomy for a Tunisian telecom operator.

This module is the single source of truth for categories and departments. It is
seeded into Mongo on first boot; after that Mongo is authoritative and this file
only bootstraps a fresh install (spec section 9).

Swapping sector = replacing this file. Nothing above it hardcodes telecom.
"""

from enum import StrEnum
from typing import NamedTuple


class Category(StrEnum):
    FACTURATION = "FACTURATION"
    PAIEMENT_RECHARGE = "PAIEMENT_RECHARGE"
    RESEAU_MOBILE = "RESEAU_MOBILE"
    INTERNET_FIXE = "INTERNET_FIXE"
    INTERVENTION_TECHNIQUE = "INTERVENTION_TECHNIQUE"
    OFFRES_ABONNEMENT = "OFFRES_ABONNEMENT"
    RESILIATION_PORTABILITE = "RESILIATION_PORTABILITE"
    SERVICE_CLIENT_AGENCE = "SERVICE_CLIENT_AGENCE"
    EQUIPEMENT = "EQUIPEMENT"
    ROAMING_INTERNATIONAL = "ROAMING_INTERNATIONAL"
    APPLICATION_MOBILE = "APPLICATION_MOBILE"


#: Deliberately no "AUTRE" class. A garbage class absorbs every hard example and
#: destroys its own precision; an unclassifiable complaint instead falls through
#: the confidence threshold into needs_human_triage (spec 5.6).
ALL_CATEGORIES: list[str] = [c.value for c in Category]

CATEGORY_LABELS_FR: dict[str, str] = {
    Category.FACTURATION: "Facturation",
    Category.PAIEMENT_RECHARGE: "Paiement et recharge",
    Category.RESEAU_MOBILE: "Réseau mobile",
    Category.INTERNET_FIXE: "Internet fixe",
    Category.INTERVENTION_TECHNIQUE: "Intervention technique",
    Category.OFFRES_ABONNEMENT: "Offres et abonnement",
    Category.RESILIATION_PORTABILITE: "Résiliation et portabilité",
    Category.SERVICE_CLIENT_AGENCE: "Service client et agence",
    Category.EQUIPEMENT: "Équipement",
    Category.ROAMING_INTERNATIONAL: "Roaming et international",
    Category.APPLICATION_MOBILE: "Application mobile",
}

CATEGORY_LABELS_AR: dict[str, str] = {
    Category.FACTURATION: "الفوترة",
    Category.PAIEMENT_RECHARGE: "الدفع والتعبئة",
    Category.RESEAU_MOBILE: "الشبكة الجوالة",
    Category.INTERNET_FIXE: "الأنترنت القار",
    Category.INTERVENTION_TECHNIQUE: "التدخل الفني",
    Category.OFFRES_ABONNEMENT: "العروض والاشتراك",
    Category.RESILIATION_PORTABILITE: "الفسخ ونقل الرقم",
    Category.SERVICE_CLIENT_AGENCE: "خدمة الحرفاء والوكالة",
    Category.EQUIPEMENT: "التجهيزات",
    Category.ROAMING_INTERNATIONAL: "التجوال والدولي",
    Category.APPLICATION_MOBILE: "التطبيق الجوال",
}


class DepartmentSeed(NamedTuple):
    code: str
    name: str
    description: str
    categories: list[str]
    keywords: list[str]
    default_sla_hours: int | None


#: The fallback department for anything unroutable (spec 5.6).
GENERAL_DEPARTMENT_CODE = "GENERAL"

DEPARTMENT_SEED: list[DepartmentSeed] = [
    DepartmentSeed(
        code="FACTURATION",
        name="Facturation et Recouvrement",
        description="Factures, prélèvements, contestations de montant, recharges et paiements.",
        categories=[Category.FACTURATION, Category.PAIEMENT_RECHARGE],
        keywords=[
            "facture", "facturation", "montant", "prelevement", "prélèvement",
            "hors forfait", "surfacturation", "recharge", "solde", "paiement",
            "d17", "e-dinar", "edinar", "remboursement", "impaye", "impayé",
            "فاتورة", "خلاص", "تعبئة", "رصيد", "مبلغ",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="RESEAU_MOBILE",
        name="Réseau Mobile",
        description="Couverture, qualité du signal, data mobile, roaming et international.",
        categories=[Category.RESEAU_MOBILE, Category.ROAMING_INTERNATIONAL],
        keywords=[
            "reseau", "réseau", "signal", "couverture", "4g", "5g", "3g",
            "coupure", "appel", "sms", "data", "debit mobile", "roaming",
            "international", "itinerance", "itinérance",
            "شبكة", "إشارة", "تغطية", "مكالمة", "أنترنت",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="FIXE_INTERVENTION",
        name="Fixe et Intervention",
        description="ADSL, fibre, ligne fixe, déplacements techniciens et rétablissement.",
        categories=[Category.INTERNET_FIXE, Category.INTERVENTION_TECHNIQUE],
        keywords=[
            "adsl", "fibre", "ligne fixe", "box", "modem", "debit", "débit",
            "deconnexion", "déconnexion", "panne", "technicien", "intervention",
            "raccordement", "installation", "derangement", "dérangement",
            "أنترنت قار", "خط", "عطب", "تدخل", "فني",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="COMMERCIAL",
        name="Commercial et Offres",
        description="Forfaits, promotions, engagements, résiliations et portabilité.",
        categories=[Category.OFFRES_ABONNEMENT, Category.RESILIATION_PORTABILITE],
        keywords=[
            "forfait", "offre", "promotion", "abonnement", "engagement",
            "resilier", "résilier", "resiliation", "résiliation", "portabilite",
            "portabilité", "changer d'operateur", "concurrent", "migration",
            "عرض", "اشتراك", "فسخ", "نقل الرقم",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="RELATION_CLIENT",
        name="Relation Client",
        description="Accueil en agence, centre d’appel, comportement, matériel et SIM.",
        categories=[Category.SERVICE_CLIENT_AGENCE, Category.EQUIPEMENT],
        keywords=[
            "agence", "guichet", "attente", "accueil", "agent", "conseiller",
            "centre d'appel", "call center", "injoignable", "sim", "puce",
            "decodeur", "décodeur", "routeur", "terminal", "materiel", "matériel",
            "وكالة", "انتظار", "موظف", "شريحة",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="DIGITAL_SI",
        name="Digital et Systèmes d’Information",
        description="Application self-care, espace client web, paiement en ligne.",
        categories=[Category.APPLICATION_MOBILE],
        keywords=[
            "application", "appli", "app", "espace client", "site web",
            "connexion", "login", "mot de passe", "bug", "plante", "crash",
            "mise a jour", "mise à jour", "notification",
            "تطبيق", "موقع", "كلمة السر", "تسجيل الدخول",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code=GENERAL_DEPARTMENT_CODE,
        name="Service Général",
        description="File d’attente de secours : réclamations non routables automatiquement.",
        categories=[],
        keywords=[],
        default_sla_hours=None,
    ),
]

#: category -> department code, derived so the two can never drift apart.
CATEGORY_TO_DEPARTMENT: dict[str, str] = {
    category: seed.code for seed in DEPARTMENT_SEED for category in seed.categories
}


def department_for_category(category: str | None) -> str:
    """Route a category to its department, falling back to GENERAL (spec 5.6)."""
    if category is None:
        return GENERAL_DEPARTMENT_CODE
    return CATEGORY_TO_DEPARTMENT.get(category, GENERAL_DEPARTMENT_CODE)
