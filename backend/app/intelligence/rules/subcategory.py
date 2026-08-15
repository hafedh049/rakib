"""Keyword-derived subcategories.

Deliberately NOT a second classifier: at roughly 80 samples per subclass a
model would be noise, while a keyword map is exact, explainable and free
(locked design decision for spec 3.1's `subcategory` field).

These terms do double duty — scripts/labeling.py builds its weak-supervision
vocabulary from them, so a term added here also sharpens the labelling of
harvested reviews.
"""

from app.domain.taxonomy import Category
from app.intelligence.rules.engine import find_terms

SUBCATEGORY_TERMS: dict[str, dict[str, list[str]]] = {
    Category.CARTE_BANCAIRE: {
        "carte_avalee": ["avalee", "avalé", "avale par", "retenue", "bloquee dans",
                         "تبلعت", "بلعت", "bel3atha"],
        "carte_bloquee": ["bloquee", "bloqué", "desactivee", "suspendue", "opposee",
                          "مسكرة", "معطلة", "msakkra"],
        "carte_non_recue": ["jamais recue", "pas recue", "non delivree", "renouvellement",
                            "ما وصلتش", "ma wsaletch"],
        "opposition": ["opposition", "faire opposition", "declarer perdue", "volee",
                       "اعتراض", "ضايعة"],
        "plafond": ["plafond", "limite de retrait", "montant maximum", "سقف"],
    },
    Category.DAB_GAB: {
        "debit_sans_billets": ["sans billet", "aucun billet", "pas de billet",
                               "n'a pas delivre", "debite mais", "ما خرجش", "ma khrajch"],
        "montant_incomplet": ["montant inferieur", "incomplet", "manque", "moins que",
                              "اقل", "na9es"],
        "distributeur_hs": ["hors service", "en panne", "ne fonctionne pas", "eteint",
                            "معطل", "5arban", "kharban"],
        "double_retrait": ["deux fois", "double", "doublon", "مرتين", "zouz marrat"],
    },
    Category.PAIEMENT_TPE_ECOMMERCE: {
        "double_debit": ["deux fois", "double debit", "doublon", "debite deux",
                         "مرتين", "zouz marrat"],
        "paiement_refuse": ["refuse", "rejete", "echec", "n'accepte pas",
                            "مرفوض", "ma khdemch"],
        "code_3ds": ["3d secure", "3ds", "code sms", "otp", "code de confirmation",
                     "الرمز", "code ma yjinich"],
        "achat_en_ligne": ["en ligne", "site marchand", "e-commerce", "internet",
                           "عبر الانترنت"],
    },
    Category.VIREMENT_PRELEVEMENT: {
        "virement_non_recu": ["non recu", "pas recu", "jamais arrive", "toujours pas",
                              "ما وصلش", "ma wsalch"],
        "virement_salaire": ["salaire", "paie", "employeur", "الاجرة", "el paie"],
        "prelevement_conteste": ["prelevement", "resilie", "sans mon accord",
                                 "اقتطاع", "prelevement"],
        "mauvais_rib": ["rib", "iban", "mauvais compte", "erreur de compte",
                        "خاطئ", "ghalet"],
        "delai_execution": ["delai", "depuis", "toujours en cours", "تاخير"],
    },
    Category.CHEQUE_EFFET: {
        "chequier_non_delivre": ["chequier", "carnet de cheque", "non delivre",
                                 "دفتر شيكات", "chekat"],
        "rejet_injustifie": ["rejete", "sans provision", "impaye", "retourne",
                             "رجع", "rja3"],
        "remise_non_creditee": ["remise", "encaissement", "non credite", "depose",
                                "ما تسجلش"],
        "opposition_cheque": ["opposition", "perdu", "vole", "اعتراض", "ضايع"],
        "certification": ["certification", "certifie", "vise", "مصادق"],
    },
    Category.COMPTE_GESTION: {
        "cloture_non_effectuee": ["cloture", "fermer", "fermeture", "toujours actif",
                                  "غلق", "nsakker"],
        "releve_non_recu": ["releve", "extrait", "non recu", "كشف حساب"],
        "compte_bloque": ["bloque", "gele", "suspendu", "sans notification",
                          "مسكر", "msakker"],
        "solde_errone": ["solde", "incorrect", "errone", "ne correspond pas",
                         "الرصيد", "ghalet"],
        "procuration": ["procuration", "mandataire", "co-titulaire", "compte joint",
                        "وكالة", "توكيل"],
    },
    Category.CREDIT_FINANCEMENT: {
        "echeance_double": ["deux fois", "double", "prelevee deux", "مرتين"],
        "mainlevee": ["mainlevee", "hypotheque", "garantie", "levee", "رفع اليد"],
        "dossier_sans_reponse": ["dossier", "sans reponse", "en attente", "toujours pas",
                                 "الملف", "bla rad"],
        "taux_conteste": ["taux", "interet", "teg", "superieur a l'offre", "نسبة"],
        "amortissement": ["amortissement", "tableau", "echeancier", "جدول التسديد"],
        "penalites": ["penalite", "retard", "majoration", "خطية"],
    },
    Category.FRAIS_COMMISSIONS: {
        "agios": ["agios", "decouvert", "interets debiteurs", "فوائد"],
        "tenue_de_compte": ["tenue de compte", "frais de gestion", "trimestre",
                            "مصاريف التصرف"],
        "commission_virement": ["commission", "frais de virement", "عمولة"],
        "frais_carte": ["frais de carte", "cotisation", "renouvellement carte",
                        "مصاريف البطاقة"],
        "frais_dossier": ["frais de dossier", "montage", "etude", "مصاريف الملف"],
    },
    Category.BANQUE_DIGITALE: {
        "connexion_impossible": ["connexion", "login", "identifiants", "mot de passe",
                                 "code d'acces", "تسجيل الدخول"],
        "plantage": ["plante", "crash", "se ferme", "bug", "ne s'ouvre pas",
                     "tetsakker", "ما يخدمش"],
        "otp_non_recu": ["otp", "code sms", "code de verification", "pas recu le code",
                         "الرمز ما جاش"],
        "operation_impossible": ["virement impossible", "echoue", "erreur technique",
                                 "ne passe pas"],
        "donnees_incorrectes": ["solde", "incorrect", "affiche", "decalage", "retard"],
    },
    Category.OPERATIONS_INTERNATIONALES: {
        "allocation_touristique": ["allocation touristique", "voyage", "devise voyage",
                                   "المنحة السياحية"],
        "transfert_non_recu": ["transfert", "swift", "non recu", "depuis l'etranger",
                               "ما وصلش"],
        "taux_de_change": ["taux de change", "change", "cours", "نسبة الصرف"],
        "carte_devise": ["carte devise", "carte internationale", "alimentee",
                         "بطاقة العملة"],
        "frais_transfert": ["frais", "commission", "a la charge de l'emetteur"],
    },
    Category.FRAUDE_OPERATION_NON_AUTORISEE: {
        "operations_inconnues": ["je n'ai jamais", "jamais effectue", "ne reconnais pas",
                                 "inconnue", "ما عملتهاش", "ma3maltehech"],
        "carte_compromise": ["carte utilisee", "a mon insu", "carte piratee", "skimming",
                             "البطاقة مسروقة"],
        "phishing": ["sms", "lien", "hameconnage", "phishing", "faux message",
                     "تصيد", "رسالة مزورة"],
        "acces_non_autorise": ["appareil inconnu", "connexion suspecte", "beneficiaire",
                               "espace pirate", "قرصنة"],
        "prelevement_frauduleux": ["organisme inconnu", "aucun contrat", "sans mon accord",
                                   "بدون علمي"],
    },
    Category.AGENCE_QUALITE_SERVICE: {
        "attente_agence": ["attente", "file", "guichet", "queue", "انتظار", "intidhar"],
        "comportement_agent": ["comportement", "desagreable", "impoli", "hausse le ton",
                               "معاملة"],
        "injoignable": ["injoignable", "personne ne repond", "ne repond pas",
                        "ما يجاوبش", "ma yjawebch"],
        "horaires": ["horaires", "ferme", "fermeture", "ouverture", "توقيت"],
        "accessibilite": ["mobilite reduite", "personnes agees", "priorite", "siege",
                          "كبار السن"],
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
