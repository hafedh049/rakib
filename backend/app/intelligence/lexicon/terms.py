"""The category lexicon.

Each term names a product or an incident outright — "chequier", "allocation
touristique", "operation non autorisee" — so one match is meaningful on its own.
Vaguer corroborating vocabulary is deliberately absent: a word like "deux fois"
fires for cards, ATMs, payments and credit alike, and adding it would blur the
categories it was meant to separate.

Terms are matched against normalised text, so they are written normalised: lower
case, no French accents, Arabic diacritics and alef/teh-marbuta folded. A term
written with an accent here would simply never match.

Weights are uniform. The classifier separates categories by *how many* terms
match and how exclusive each one is (see the inverse-category-frequency
discount), not by hand-tuned per-term scores nobody could justify.
"""

from app.domain.taxonomy import Category

DECISIVE_WEIGHT = 3.0

#: category -> the terms that name it. Editable by an administrator; adding a
#: term is the whole procedure for teaching the system a new phrasing.
DECISIVE_TERMS: dict[str, list[str]] = {
    Category.CARTE_BANCAIRE: [
        "carte avalee", "carte bloquee", "opposition carte", "renouvellement de carte",
        "plafond de retrait", "carte bancaire", "carte visa", "carte cib",
        "البطاقة تبلعت", "البطاقة مسكرة", "البطاقة البنكية",
    ],
    Category.DAB_GAB: [
        "distributeur", "guichet automatique", "dab", "gab", "sans billet",
        "aucun billet", "n'a pas delivre", "retrait rate",
        "الموزع الآلي", "الموزع",
    ],
    Category.PAIEMENT_TPE_ECOMMERCE: [
        "tpe", "terminal de paiement", "3d secure", "3ds", "paiement en ligne",
        "achat en ligne", "chez le commercant", "site marchand",
        "الدفع الالكتروني", "الخلاص بالبطاقة",
    ],
    Category.VIREMENT_PRELEVEMENT: [
        "virement", "prelevement", "rib", "iban", "virement de salaire",
        "virement permanent", "ordre de virement", "domiciliation",
        "تحويل", "اقتطاع",
    ],
    Category.CHEQUE_EFFET: [
        "cheque", "chequier", "sans provision", "remise de cheque", "effet",
        "traite", "certification de cheque", "carnet de cheque",
        "شيك", "دفتر شيكات", "كمبيالة",
    ],
    Category.COMPTE_GESTION: [
        "cloture de compte", "releve de compte", "compte bloque", "compte joint",
        "procuration", "ouverture de compte", "extrait de compte",
        "كشف حساب", "غلق الحساب", "الحساب مسكر",
    ],
    Category.CREDIT_FINANCEMENT: [
        "credit", "pret", "echeance", "mainlevee", "tableau d'amortissement",
        "credit logement", "credit auto", "credit consommation", "hypotheque",
        "قرض", "قسط", "رفع اليد",
    ],
    Category.FRAIS_COMMISSIONS: [
        "agios", "frais de tenue de compte", "commission", "frais de dossier",
        "frais de carte", "cotisation annuelle", "tarification",
        "مصاريف", "عمولة", "مصاريف التصرف",
    ],
    Category.BANQUE_DIGITALE: [
        "application", "l'appli", "cette appli", "mise a jour de l'application",
        "se connecter a l'application", "espace en ligne", "code d'acces",
        "mobile banking", "e-banking", "espace client",
        "التطبيق", "app crash", "the app",
    ],
    Category.OPERATIONS_INTERNATIONALES: [
        "allocation touristique", "transfert international", "taux de change",
        "carte devise", "swift", "compte en devises", "rapatriement",
        "المنحة السياحية", "تحويل خارجي", "الصرف",
    ],
    Category.FRAUDE_OPERATION_NON_AUTORISEE: [
        "operation non autorisee", "operations non autorisees",
        "je n'ai jamais autorise", "je n'ai jamais effectue", "je n'ai pas effectue",
        "compte pirate", "carte piratee", "hameconnage", "phishing", "skimming",
        "ne reconnais pas", "a mon insu", "sans mon accord",
        "عملية غير مصرح بها", "ما عملتهاش", "قرصنة",
    ],
    Category.AGENCE_QUALITE_SERVICE: [
        "agence", "guichet", "chargee de clientele", "charge de clientele",
        "file d'attente", "accueil en agence", "conseiller",
        "الوكالة", "خدمة الحرفاء", "الانتظار",
    ],
}


def build_lexicon() -> dict[str, dict[str, float]]:
    """category -> {term: weight}, lower-cased for matching."""
    return {
        category: {term.lower(): DECISIVE_WEIGHT for term in terms}
        for category, terms in DECISIVE_TERMS.items()
    }


#: Built once at import. Rebuilding is cheap, but the engine holds a reference
#: and a stable dict keeps the IDF table stable too.
CATEGORY_LEXICON: dict[str, dict[str, float]] = build_lexicon()
