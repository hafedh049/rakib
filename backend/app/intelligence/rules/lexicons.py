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
    "poursuites", "poursuites judiciaires", "action en justice", "contentieux",
    "litige", "recours", "arbitrage", "dommages et interets", "prejudice",
    "inpdp", "donnees personnelles", "loi", "reglementation", "sanction",
]

LEGAL_AR = [
    "محامي", "شكايه", "شكايه رسميه", "محكمه", "قضاء", "قضيه", "عدل منفذ",
    "انذار", "المعهد الوطني للاستهلاك", "حمايه المستهلك", "تعويض", "ضرر",
    "متابعه قضائيه", "قانون", "حقي", "حقوقي",
]

# --------------------------------------------------------------------------- médiation
#: Invoking the banking mediator is a distinct signal from a generic legal
#: threat: under the décret n°2006-1881 the customer must come to the bank
#: first, so naming the mediator means the internal path is being judged to have
#: failed. Article 2 of the circulaire also puts a complaint *already* seized by
#: the mediator outside its scope entirely — see HorsPerimetre.SAISINE_MEDIATEUR.
MEDIATEUR_FR = [
    "mediateur", "mediateur bancaire", "mediation", "mediation bancaire",
    "saisir le mediateur", "banque centrale", "bct", "banque centrale de tunisie",
    "observatoire de l'inclusion financiere", "oif", "autorite de controle",
    "je saisirai", "je vais saisir", "escalader a la banque centrale",
]

MEDIATEUR_AR = [
    "الوسيط البنكي", "الوسيط", "وساطه", "البنك المركزي", "البنك المركزي التونسي",
    "مرصد الادماج المالي", "نشكي للبنك المركزي", "سلطه الرقابه",
]

# ----------------------------------------------------------------------------- fraude
#: The highest-weight signal in a banking complaint system. An unauthorised debit
#: is money already gone; it is also the one category where the bank's own delay
#: compounds the customer's loss.
FRAUDE_FR = [
    "fraude", "frauduleux", "frauduleuse", "operation non autorisee",
    "operations non autorisees", "transaction non autorisee", "debit non autorise",
    "prelevement non autorise", "sans mon accord", "sans mon autorisation",
    "je n'ai jamais autorise", "je n'ai pas effectue", "je n'ai jamais effectue",
    "ce n'est pas moi", "piratage", "pirate", "compte pirate", "carte piratee",
    "hameconnage", "phishing", "skimming", "usurpation", "usurpation d'identite",
    "vol de carte", "carte volee", "detournement", "retrait non effectue",
    "debit inconnu", "operation inconnue", "je ne reconnais pas",
]

FRAUDE_AR = [
    "احتيال", "عمليه غير مصرح بها", "عمليات غير مصرح بها", "خصم غير مصرح به",
    "بدون علمي", "بدون موافقتي", "ما عملتهاش", "موش انا", "قرصنه", "تم اختراق",
    "سرقه البطاقه", "بطاقتي مسروقه", "تصيد", "انتحال", "عمليه ما نعرفهاش",
]

FRAUDE_TN = [
    "ma3maltehech", "mouch ana", "sara9ou", "sar9ouli", "piratage",
    "5ada flous", "khada flousi", "bla ma na3ref", "ma3ndich 3lem",
    "3malou 3ملية", "flous tar", "flousi mchew",
]

# ----------------------------------------------------------------------------- churn
CHURN_FR = [
    "cloturer mon compte", "cloture de compte", "fermer mon compte",
    "fermer mes comptes", "changer de banque", "changer de banques",
    "transferer mes avoirs", "transferer mon compte", "domicilier ailleurs",
    "domiciliation ailleurs", "rapatrier mes fonds", "retirer mon argent",
    "retirer tous mes fonds", "concurrence", "une autre banque", "chez la concurrence",
    "quitter la banque", "je pars", "je vous quitte", "resilier ma carte",
    "resilier mes services", "ne plus jamais", "aller ailleurs",
    "mon salaire sera domicilie ailleurs", "arreter la relation",
]

CHURN_TN = [
    "nhabet nsakker", "nsakker el compte", "nsakker sahbi", "nbadel banque",
    "nhab nbadel banka", "nemchi l banque okhra", "3andhom ahsen",
    "bech nekhrej flousi", "nekhou flousi", "nhawel flousi",
]

CHURN_AR = [
    "نغلق حسابي", "غلق الحساب", "نسكر الحساب", "نبدل بنك", "بنك اخر",
    "نحول حسابي", "نسحب فلوسي", "نسحب اموالي", "ما نحبش نكمل معاكم",
    "نمشي لبنك اخر",
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
    "MEDIATEUR_FR": MEDIATEUR_FR,
    "MEDIATEUR_AR": MEDIATEUR_AR,
    "FRAUDE_FR": FRAUDE_FR,
    "FRAUDE_AR": FRAUDE_AR,
    "FRAUDE_TN": FRAUDE_TN,
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
    | set(FRAUDE_FR) | set(FRAUDE_AR) | set(FRAUDE_TN)
    | set(PROFANITY)
)
