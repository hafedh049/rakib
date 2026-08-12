"""Lexicons for the rules engine — French, Arabic and Tunisian derja.

These seed Mongo on first boot; after that the admin UI edits them and Mongo is
authoritative (spec section 9). Terms are matched against the normalised text,
so they must be written in normalised form: lower case, no Arabic diacritics,
alef and teh-marbuta already folded.
"""

# --------------------------------------------------------------------------- urgency
URGENCY_FR = [
    "urgent", "urgence", "tres urgent", "immediat", "immediatement", "au plus vite",
    "sans delai", "inacceptable", "inadmissible", "scandaleux", "honteux",
    "intolerable", "insupportable", "depuis des semaines", "depuis des mois",
    "depuis un mois", "toujours pas", "toujours rien", "aucune reponse",
    "aucune solution", "personne ne repond", "cela fait", "ras le bol",
    "j'en ai assez", "trop c'est trop", "derniere fois", "dernier avertissement",
    "je perds patience", "situation critique", "gravement", "catastrophe",
    "impossible de travailler", "je suis bloque", "totalement bloque",
    "plus rien ne fonctionne", "coupure totale", "aucun service", "hors service",
    "priorite", "escalade", "responsable", "direction", "reclamation formelle",
]

URGENCY_AR = [
    "مستعجل", "عاجل", "بسرعه", "حالا", "فورا", "غير مقبول", "غير معقول",
    "من اسابيع", "من شهر", "من شهور", "مازال", "ما زال", "حتي الان",
    "ما فماش حل", "ما ثماش حل", "محتاج حل", "مشكل كبير", "كارثه",
    "ما ينجمش", "توقف", "منقطع", "بلا خدمه", "مسؤول", "الاداره", "شكوي رسميه",
]

URGENCY_TN = [
    "3andi mochkla", "mochkel kbir", "barcha", "barsha", "9adech", "ma3adech",
    "yezzi", "ma yenjemch", "ma khedmetch", "mazel", "ma zelt", "3ala khater",
    "3awtani", "kol nhar", "semaine kamla", "chhar kaml", "hatta hne",
    "ma7adech", "ma 7atetch", "sayeb", "mriguel", "t3abt",
]

# ----------------------------------------------------------------------------- legal
LEGAL_FR = [
    "avocat", "plainte", "porter plainte", "tribunal", "justice", "juridique",
    "mise en demeure", "huissier", "constat d'huissier", "inc",
    "institut national de la consommation", "protection du consommateur",
    "organisation de defense du consommateur", "instance", "regulateur",
    "instance nationale des telecommunications", "intt", "poursuites",
    "poursuites judiciaires", "action en justice", "contentieux", "litige",
    "recours", "mediateur", "arbitrage", "dommages et interets", "prejudice",
    "inpdp", "donnees personnelles", "loi", "reglementation", "sanction",
]

LEGAL_AR = [
    "محامي", "شكايه", "شكايه رسميه", "محكمه", "قضاء", "قضيه", "عدل منفذ",
    "انذار", "المعهد الوطني للاستهلاك", "حمايه المستهلك", "تعويض", "ضرر",
    "متابعه قضائيه", "قانون", "حقي", "حقوقي",
]

# ----------------------------------------------------------------------------- churn
CHURN_FR = [
    "resilier", "resiliation", "annuler mon abonnement", "annulation",
    "changer d'operateur", "changer operateur", "concurrent", "portabilite",
    "porter mon numero", "quitter", "je pars", "je vous quitte", "fermer ma ligne",
    "cloturer mon compte", "arreter le service", "ne plus jamais",
    "aller ailleurs", "autre operateur", "chez la concurrence", "desabonner",
]

CHURN_TN = [
    "nhabet nbadel", "nbadel operateur", "nhab nfasakh", "fasakh", "nsakker",
    "nemchi l", "3andhom ahsen", "bech nbadel", "nekhrej",
]

CHURN_AR = [
    "نفسخ", "فسخ", "نبدل مشغل", "نقل الرقم", "نسكر الخط", "نمشي لعند",
    "الغاء الاشتراك", "ما نحبش نكمل",
]

# ------------------------------------------------------------------------- profanity
#: Not for moralising — a complaint containing abuse needs a human, not a bot.
PROFANITY = [
    "merde", "putain", "connard", "imbecile", "incompetent", "incompetents",
    "voleurs", "voleur", "arnaque", "arnaqueurs", "escroquerie", "escrocs",
    "nuls", "honte", "7ram", "haram", "sarka", "sara9", "nasb",
    "حرام", "سرقه", "نصب", "كذب",
]

# -------------------------------------------------------------------------- positive
POSITIVE_FR = [
    "merci", "merci beaucoup", "satisfait", "tres satisfait", "content",
    "felicitations", "excellent", "parfait", "rapide", "efficace", "professionnel",
    "aimable", "serviable", "resolu", "regle", "bravo", "appreciable",
    "bonne prise en charge", "reactif",
]

POSITIVE_AR = [
    "شكرا", "برشا شكرا", "راضي", "مبروك", "ممتاز", "بريز", "تبارك الله",
    "خدمه ممتازه", "سريع",
]

POSITIVE_TN = ["barcha shokran", "yaatik saha", "ya3tik el sa7a", "behi", "mrigel"]

# -------------------------------------------------------------------------- negative
NEGATIVE_FR = [
    "mecontent", "decu", "deception", "insatisfait", "mauvais", "mauvaise",
    "lent", "lenteur", "penible", "desagreable", "incorrect", "errone",
    "erreur", "probleme", "panne", "coupure", "defaillance", "dysfonctionnement",
    "impossible", "echec", "bloque", "retard", "attente", "jamais",
]

NEGATIVE_AR = [
    "مشكل", "مشكله", "عطب", "انقطاع", "خطا", "غالط", "بطيء", "ما يخدمش",
    "ما نجمتش", "تاخير", "انتظار", "مش راضي", "خايب",
]

NEGATIVE_TN = [
    "mochkel", "mochkla", "ma yekhdemch", "khayeb", "batee", "3otob",
    "ma nejemtech", "t3atal", "sob",
]

# ------------------------------------------------------------------------- negation
#: A negation flips polarity for the next few tokens: "pas satisfait" is
#: negative even though "satisfait" is a positive term (spec 5.4).
NEGATIONS_FR = ["pas", "plus", "jamais", "aucun", "aucune", "ni", "sans", "non", "rien"]
NEGATIONS_AR = ["ما", "مش", "موش", "لا", "بلا", "ماش"]
NEGATIONS_TN = ["ma", "mouch", "mech", "mesh", "bla", "manich", "mahouch"]

NEGATION_WINDOW = 3

LEXICONS: dict[str, list[str]] = {
    "URGENCY_FR": URGENCY_FR,
    "URGENCY_AR": URGENCY_AR,
    "URGENCY_TN": URGENCY_TN,
    "LEGAL_FR": LEGAL_FR,
    "LEGAL_AR": LEGAL_AR,
    "CHURN_FR": CHURN_FR,
    "CHURN_AR": CHURN_AR,
    "CHURN_TN": CHURN_TN,
    "PROFANITY": PROFANITY,
    "POSITIVE_FR": POSITIVE_FR,
    "POSITIVE_AR": POSITIVE_AR,
    "POSITIVE_TN": POSITIVE_TN,
    "NEGATIVE_FR": NEGATIVE_FR,
    "NEGATIVE_AR": NEGATIVE_AR,
    "NEGATIVE_TN": NEGATIVE_TN,
}

ALL_NEGATIONS = set(NEGATIONS_FR) | set(NEGATIONS_AR) | set(NEGATIONS_TN)

POSITIVE_TERMS = set(POSITIVE_FR) | set(POSITIVE_AR) | set(POSITIVE_TN)
NEGATIVE_TERMS = (
    set(NEGATIVE_FR) | set(NEGATIVE_AR) | set(NEGATIVE_TN)
    | set(URGENCY_FR) | set(URGENCY_AR) | set(URGENCY_TN)
    | set(PROFANITY)
)
