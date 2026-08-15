"""The category lexicon: terms, and how much each is worth.

Two tiers, because not all evidence is equal:

*   **Decisive** terms name the product or the incident outright — "chequier",
    "allocation touristique", "operation non autorisee". One of them is usually
    enough on its own.
*   **Supporting** terms are the subcategory vocabulary. They are shared far
    more widely ("deux fois" fires for cards, ATMs, payments and credit alike),
    so they only corroborate.

Terms are matched against normalised text, so they must be written normalised:
lower case, no French accents, Arabic diacritics and alef/teh-marbuta folded.

The weights below are the seed. They are deliberately coarse — a 3/1 split
rather than tuned decimals — because a number an administrator cannot reason
about is worse than a blunt one they can.
"""

from app.domain.taxonomy import Category
from app.intelligence.rules.subcategory import SUBCATEGORY_TERMS

DECISIVE_WEIGHT = 3.0
SUPPORTING_WEIGHT = 1.0

#: Terms that name the product or the incident. Moved here from the dev-time
#: weak-supervision script, which is now the *consumer* of this file rather
#: than the owner of its own copy — one vocabulary, one place to edit it.
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
    """category -> {term: weight}, decisive terms overriding supporting ones."""
    lexicon: dict[str, dict[str, float]] = {}
    for category, subcategories in SUBCATEGORY_TERMS.items():
        terms: dict[str, float] = {}
        for subcategory_terms in subcategories.values():
            for term in subcategory_terms:
                terms[term.lower()] = SUPPORTING_WEIGHT
        lexicon[category] = terms

    for category, decisive in DECISIVE_TERMS.items():
        terms = lexicon.setdefault(category, {})
        for term in decisive:
            terms[term.lower()] = DECISIVE_WEIGHT

    return lexicon


#: Built once at import. Rebuilding is cheap, but the engine holds a reference
#: and a stable dict keeps the IDF table stable too.
CATEGORY_LEXICON: dict[str, dict[str, float]] = build_lexicon()
