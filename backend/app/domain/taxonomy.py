"""The complaint taxonomy for a Tunisian bank.

This module is the single source of truth for categories, regulatory objects and
departments. It is seeded into Mongo on first boot; after that Mongo is
authoritative and this file only bootstraps a fresh install (spec section 9).

Swapping sector = replacing this file. Nothing above it hardcodes banking — the
previous revision of this same file described a telecom operator, and the six
pipeline stages, the rules engine, RBAC, the SLA calendar and the deployment
were untouched by the change.

Two levels of classification, and they must never drift apart:

*   `Category` is what the **bank** routes on — fine-grained, what an agent
    actually works with, what the classifier predicts.
*   `ObjetBCT` is what the **regulator** counts. Circulaire BCT n°2022-08,
    Annexe 3, section IV ventilates complaints across exactly eight objects, and
    that annual declaration is a legal obligation (code ROGS760, annual,
    DR+45 days, XML).

`OBJET_FOR_CATEGORY` derives the second from the first, so a new category cannot
be added without deciding how the regulator will see it.
"""

from enum import StrEnum
from typing import NamedTuple


class Category(StrEnum):
    """What the bank routes on."""

    CARTE_BANCAIRE = "CARTE_BANCAIRE"
    DAB_GAB = "DAB_GAB"
    PAIEMENT_TPE_ECOMMERCE = "PAIEMENT_TPE_ECOMMERCE"
    VIREMENT_PRELEVEMENT = "VIREMENT_PRELEVEMENT"
    CHEQUE_EFFET = "CHEQUE_EFFET"
    COMPTE_GESTION = "COMPTE_GESTION"
    CREDIT_FINANCEMENT = "CREDIT_FINANCEMENT"
    FRAIS_COMMISSIONS = "FRAIS_COMMISSIONS"
    BANQUE_DIGITALE = "BANQUE_DIGITALE"
    OPERATIONS_INTERNATIONALES = "OPERATIONS_INTERNATIONALES"
    FRAUDE_OPERATION_NON_AUTORISEE = "FRAUDE_OPERATION_NON_AUTORISEE"
    AGENCE_QUALITE_SERVICE = "AGENCE_QUALITE_SERVICE"


class ObjetBCT(StrEnum):
    """The eight objects of Annexe 3-IV. Not ours to rename — the regulator's."""

    FINANCEMENT = "FINANCEMENT"
    PAIEMENT_HORS_MONETIQUE = "PAIEMENT_HORS_MONETIQUE"
    MONETIQUE = "MONETIQUE"
    FONCTIONNEMENT_COMPTES = "FONCTIONNEMENT_COMPTES"
    OPERATIONS_INTERNATIONALES = "OPERATIONS_INTERNATIONALES"
    TARIFICATION = "TARIFICATION"
    SERVICES_A_DISTANCE = "SERVICES_A_DISTANCE"
    AUTRES_SERVICES = "AUTRES_SERVICES"


#: Deliberately no "AUTRE" class. A garbage class absorbs every hard example and
#: destroys its own precision; an unclassifiable complaint instead falls through
#: the confidence threshold into needs_human_triage (spec 5.6). Note that the
#: regulator's own "Autres services" is an *objet*, not a category — it is the
#: bucket for agency-quality complaints, not for the classifier's failures.
ALL_CATEGORIES: list[str] = [c.value for c in Category]
ALL_OBJETS: list[str] = [o.value for o in ObjetBCT]

CATEGORY_LABELS_FR: dict[str, str] = {
    Category.CARTE_BANCAIRE: "Carte bancaire",
    Category.DAB_GAB: "Distributeur (DAB/GAB)",
    Category.PAIEMENT_TPE_ECOMMERCE: "Paiement TPE et e-commerce",
    Category.VIREMENT_PRELEVEMENT: "Virement et prélèvement",
    Category.CHEQUE_EFFET: "Chèque et effet",
    Category.COMPTE_GESTION: "Gestion du compte",
    Category.CREDIT_FINANCEMENT: "Crédit et financement",
    Category.FRAIS_COMMISSIONS: "Frais et commissions",
    Category.BANQUE_DIGITALE: "Banque digitale",
    Category.OPERATIONS_INTERNATIONALES: "Opérations internationales",
    Category.FRAUDE_OPERATION_NON_AUTORISEE: "Fraude / opération non autorisée",
    Category.AGENCE_QUALITE_SERVICE: "Agence et qualité de service",
}

CATEGORY_LABELS_AR: dict[str, str] = {
    Category.CARTE_BANCAIRE: "البطاقة البنكية",
    Category.DAB_GAB: "الموزع الآلي",
    Category.PAIEMENT_TPE_ECOMMERCE: "الدفع الإلكتروني",
    Category.VIREMENT_PRELEVEMENT: "التحويل والاقتطاع",
    Category.CHEQUE_EFFET: "الشيك والكمبيالة",
    Category.COMPTE_GESTION: "التصرف في الحساب",
    Category.CREDIT_FINANCEMENT: "القرض والتمويل",
    Category.FRAIS_COMMISSIONS: "المصاريف والعمولات",
    Category.BANQUE_DIGITALE: "البنك الرقمي",
    Category.OPERATIONS_INTERNATIONALES: "العمليات الدولية",
    Category.FRAUDE_OPERATION_NON_AUTORISEE: "عملية غير مصرح بها",
    Category.AGENCE_QUALITE_SERVICE: "الوكالة وجودة الخدمة",
}

#: Annexe 3-IV wording, verbatim. These strings appear in the declaration filed
#: with the BCT, so they are not ours to prettify.
OBJET_LABELS_FR: dict[str, str] = {
    ObjetBCT.FINANCEMENT: "Financement",
    ObjetBCT.PAIEMENT_HORS_MONETIQUE: "Paiement hors monétique",
    ObjetBCT.MONETIQUE: "Monétique",
    ObjetBCT.FONCTIONNEMENT_COMPTES: "Fonctionnement des comptes",
    ObjetBCT.OPERATIONS_INTERNATIONALES: "Opérations bancaires internationales",
    ObjetBCT.TARIFICATION: "Tarification",
    ObjetBCT.SERVICES_A_DISTANCE: "Services bancaires à distance",
    ObjetBCT.AUTRES_SERVICES: "Autres services",
}

#: category -> regulatory object. Every category must appear here; the module
#: asserts totality at import time rather than discovering a hole at reporting
#: time, forty-five days after the close of the financial year.
OBJET_FOR_CATEGORY: dict[str, str] = {
    Category.CARTE_BANCAIRE: ObjetBCT.MONETIQUE,
    Category.DAB_GAB: ObjetBCT.MONETIQUE,
    Category.PAIEMENT_TPE_ECOMMERCE: ObjetBCT.MONETIQUE,
    # A disputed debit is overwhelmingly a card debit; the regulator has no
    # "fraud" object, so it is counted as monétique and carries its weight
    # through the FRAUDE_SUSPECTEE rule instead.
    Category.FRAUDE_OPERATION_NON_AUTORISEE: ObjetBCT.MONETIQUE,
    Category.VIREMENT_PRELEVEMENT: ObjetBCT.PAIEMENT_HORS_MONETIQUE,
    Category.CHEQUE_EFFET: ObjetBCT.PAIEMENT_HORS_MONETIQUE,
    Category.COMPTE_GESTION: ObjetBCT.FONCTIONNEMENT_COMPTES,
    Category.CREDIT_FINANCEMENT: ObjetBCT.FINANCEMENT,
    Category.FRAIS_COMMISSIONS: ObjetBCT.TARIFICATION,
    Category.BANQUE_DIGITALE: ObjetBCT.SERVICES_A_DISTANCE,
    Category.OPERATIONS_INTERNATIONALES: ObjetBCT.OPERATIONS_INTERNATIONALES,
    Category.AGENCE_QUALITE_SERVICE: ObjetBCT.AUTRES_SERVICES,
}

assert set(OBJET_FOR_CATEGORY) == set(Category), (
    "every category must map to a BCT object — the annual declaration has no "
    "'unmapped' column"
)


def objet_for_category(category: str | None) -> str | None:
    """Regulatory object for a category, or None while triage is undecided."""
    if category is None:
        return None
    return OBJET_FOR_CATEGORY.get(category)


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
        code="MONETIQUE",
        name="Monétique et Cartes",
        description="Cartes bancaires, distributeurs, TPE et paiement en ligne.",
        categories=[
            Category.CARTE_BANCAIRE,
            Category.DAB_GAB,
            Category.PAIEMENT_TPE_ECOMMERCE,
        ],
        keywords=[
            "carte", "carte bancaire", "cib", "visa", "mastercard", "carte avalee",
            "carte avalée", "opposition", "code pin", "code confidentiel",
            "carte bloquee", "carte bloquée", "plafond", "retrait", "distributeur",
            "dab", "gab", "guichet automatique", "billets", "tpe", "paiement en ligne",
            "e-commerce", "3d secure", "transaction refusee", "transaction refusée",
            "بطاقة", "الموزع الآلي", "سحب", "رمز سري", "معاملة",
            "karta", "distributeur", "code",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="OPERATIONS",
        name="Opérations Bancaires",
        description="Virements, prélèvements, chèques, effets et domiciliations.",
        categories=[Category.VIREMENT_PRELEVEMENT, Category.CHEQUE_EFFET],
        keywords=[
            "virement", "rib", "iban", "ordre de virement", "prelevement",
            "prélèvement", "domiciliation", "transfert interne", "beneficiaire",
            "bénéficiaire", "cheque", "chèque", "chequier", "chéquier",
            "sans provision", "certification", "opposition cheque", "effet", "traite",
            "remise", "encaissement", "compensation",
            "تحويل", "شيك", "دفتر شيكات", "كمبيالة", "اقتطاع", "رصيد غير كاف",
            "virement", "chek", "chekat",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="CREDITS",
        name="Crédits et Financement",
        description="Crédits, échéances, taux, mainlevées et dossiers de financement.",
        categories=[Category.CREDIT_FINANCEMENT],
        keywords=[
            "credit", "crédit", "pret", "prêt", "financement", "echeance", "échéance",
            "tableau d'amortissement", "amortissement", "taux", "mainlevee",
            "mainlevée", "differe", "différé", "credit auto", "credit logement",
            "credit consommation", "dossier de credit", "garantie", "hypotheque",
            "hypothèque", "remboursement anticipe", "remboursement anticipé",
            "قرض", "تمويل", "قسط", "نسبة الفائدة", "رفع اليد", "جدول التسديد",
            "credit", "9ist", "9ard",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="RELATION_CLIENT",
        name="Relation Clientèle",
        description="Comptes, tarification, accueil en agence et qualité de service.",
        categories=[
            Category.COMPTE_GESTION,
            Category.FRAIS_COMMISSIONS,
            Category.AGENCE_QUALITE_SERVICE,
        ],
        keywords=[
            "compte", "releve", "relevé", "solde", "cloture", "clôture", "ouverture",
            "procuration", "compte joint", "compte bloque", "compte bloqué",
            "agios", "frais", "commission", "tenue de compte", "frais de dossier",
            "tarification", "prelevement de frais", "agence", "guichet", "attente",
            "accueil", "charge de clientele", "chargé de clientèle", "conseiller",
            "comportement", "horaires", "file d'attente",
            "حساب", "كشف حساب", "رصيد", "غلق الحساب", "مصاريف", "عمولة",
            "وكالة", "انتظار", "موظف", "استقبال",
            "sahb", "frais", "agence", "wakala",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="DIGITAL",
        name="Banque Digitale",
        description="Application mobile, espace client en ligne et services à distance.",
        categories=[Category.BANQUE_DIGITALE],
        keywords=[
            "application", "appli", "app", "mobile banking", "e-banking",
            "espace client", "site web", "connexion", "login", "mot de passe",
            "code d'acces", "code d'accès", "otp", "sms", "notification", "bug",
            "plante", "crash", "mise a jour", "mise à jour", "authentification",
            "تطبيق", "الموقع", "كلمة السر", "تسجيل الدخول", "رمز",
            "application", "site",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="INTERNATIONAL",
        name="Opérations Internationales",
        description="Change, allocation touristique, devises et transferts internationaux.",
        categories=[Category.OPERATIONS_INTERNATIONALES],
        keywords=[
            "change", "devise", "devises", "allocation touristique", "carte devise",
            "transfert international", "swift", "western union", "moneygram",
            "rapatriement", "dinar convertible", "compte en devises", "euro",
            "dollar", "virement international", "commerce exterieur",
            "commerce extérieur", "domiciliation import",
            "صرف", "عملة", "منحة سياحية", "تحويل خارجي", "عملة صعبة",
            "devise", "change",
        ],
        default_sla_hours=None,
    ),
    DepartmentSeed(
        code="CONFORMITE_FRAUDE",
        name="Conformité et Lutte contre la Fraude",
        description="Opérations non autorisées, fraude, hameçonnage et litiges sensibles.",
        categories=[Category.FRAUDE_OPERATION_NON_AUTORISEE],
        keywords=[
            "fraude", "operation non autorisee", "opération non autorisée",
            "debit frauduleux", "débit frauduleux", "piratage", "pirate",
            "hameconnage", "hameçonnage", "phishing", "skimming", "usurpation",
            "vol de carte", "compte pirate", "compte piraté", "arnaque", "escroquerie",
            "sans mon accord", "je n'ai jamais autorise", "je n'ai jamais autorisé",
            "احتيال", "عملية غير مصرح بها", "قرصنة", "سرقة", "نصب", "بدون علمي",
            "fraude", "sr9ou", "piratage",
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

assert set(CATEGORY_TO_DEPARTMENT) == set(Category), (
    "every category must belong to exactly one department"
)


def department_for_category(category: str | None) -> str:
    """Route a category to its department, falling back to GENERAL (spec 5.6)."""
    if category is None:
        return GENERAL_DEPARTMENT_CODE
    return CATEGORY_TO_DEPARTMENT.get(category, GENERAL_DEPARTMENT_CODE)
