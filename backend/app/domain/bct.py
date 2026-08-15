"""Circulaire BCT n°2022-08 du 20 octobre 2022 — the regulatory layer.

Every constant here traces to an article of the circulaire, and the article is
cited beside it. This module exists so that a legal obligation is never buried
inside a service: when the regulator amends the circulaire, this is the file that
changes.

    Objet : Politiques et mesures de traitement des réclamations de la clientèle.

The circulaire is, in effect, the requirements document for this project.
Article 9 mandates a dedicated IT solution that centralises complaints in a
database ventilated by object and outcome, generates automated acknowledgements
carrying a reference number, alerts the handling structure on delay breaches,
and produces key performance indicators.
"""

from enum import StrEnum

CIRCULAIRE = "BCT n°2022-08 du 20 octobre 2022"
DECRET_MEDIATEUR = "Décret n°2006-1881 du 10 juillet 2006"

# --------------------------------------------------------------------- délais
#: Article 8 : « Ce délai ne dépasse pas dans tous les cas quinze (15) jours
#: ouvrables à partir de la date de l'accusé de réception. »
#:
#: This is a ceiling, not a target, and it runs from the acknowledgement — not
#: from receipt. Because it is counted in *jours ouvrables*, the Tunisian working
#: calendar (weekends, public holidays, the lunar feast table) is load-bearing:
#: a complaint acknowledged the day before Aïd is not late four days later.
DELAI_LEGAL_JOURS_OUVRABLES = 15

#: Article 8 also says the delay must « [tenir] compte de la nature de la
#: réclamation ainsi que de sa complexité », which is explicit regulatory
#: authority for differentiated internal targets. These sit below the ceiling;
#: none may exceed it, and the module asserts that below.
DELAI_INTERNE_JOURS_OUVRABLES: dict[str, int] = {
    "FRAUDE_OPERATION_NON_AUTORISEE": 2,
    "CARTE_BANCAIRE": 5,
    "DAB_GAB": 5,
    "VIREMENT_PRELEVEMENT": 5,
    "BANQUE_DIGITALE": 5,
    "PAIEMENT_TPE_ECOMMERCE": 7,
    "CHEQUE_EFFET": 7,
    "COMPTE_GESTION": 7,
    "FRAIS_COMMISSIONS": 7,
    "CREDIT_FINANCEMENT": 10,
    "OPERATIONS_INTERNATIONALES": 10,
    "AGENCE_QUALITE_SERVICE": 10,
}

assert all(
    days <= DELAI_LEGAL_JOURS_OUVRABLES
    for days in DELAI_INTERNE_JOURS_OUVRABLES.values()
), "an internal target may never exceed the legal ceiling of Article 8"


def delai_jours_ouvrables(category: str | None) -> int:
    """Working days allowed for a substantive reply, per Article 8.

    An unclassified complaint gets the legal ceiling: we may not invent a
    shorter deadline for something we have not understood yet.
    """
    if category is None:
        return DELAI_LEGAL_JOURS_OUVRABLES
    return DELAI_INTERNE_JOURS_OUVRABLES.get(category, DELAI_LEGAL_JOURS_OUVRABLES)


# ----------------------------------------------------------------- périmètre
class HorsPerimetre(StrEnum):
    """Article 2 — what is *not* a réclamation.

    A message falling in one of these buckets is still handled by the bank, but
    it is excluded from the circulaire's scope and must not inflate the annual
    declaration. Detecting them is a classification task in its own right.
    """

    DEMANDE_SERVICE = "DEMANDE_SERVICE"
    DEMANDE_INFORMATION = "DEMANDE_INFORMATION"
    SAISINE_MEDIATEUR = "SAISINE_MEDIATEUR"
    AFFAIRE_JUDICIAIRE = "AFFAIRE_JUDICIAIRE"
    LITIGE_DEJA_TRANCHE = "LITIGE_DEJA_TRANCHE"
    RAPPORT_DE_TRAVAIL = "RAPPORT_DE_TRAVAIL"


HORS_PERIMETRE_LABELS_FR: dict[str, str] = {
    HorsPerimetre.DEMANDE_SERVICE: "Demande de service",
    HorsPerimetre.DEMANDE_INFORMATION: "Demande d’information ou de conseil",
    HorsPerimetre.SAISINE_MEDIATEUR: "Déjà saisie par le médiateur bancaire",
    HorsPerimetre.AFFAIRE_JUDICIAIRE: "Affaire en cours devant la justice ou en arbitrage",
    HorsPerimetre.LITIGE_DEJA_TRANCHE: "Litige déjà tranché ou réglé à l’amiable",
    HorsPerimetre.RAPPORT_DE_TRAVAIL: "Rapport de travail entre l’établissement et un employé",
}


# ------------------------------------------------------------------ annexe 1
#: Annexe 1 : « Informations minimales à conserver par les établissements sur
#: les réclamants ». Kept as a checklist so a schema change that drops one of
#: them fails a test rather than a regulatory audit.
ANNEXE_1_CHAMPS: tuple[str, ...] = (
    "numero_reference",
    "nom_ou_raison_sociale",
    "identifiant_rne",  # personnes morales
    "date_reception",
    "canal_reception",
    "type_produit_service",
    "objet_et_description",
    "investigations_menees",
    "demarches_entreprises",
    "sort_reclamation",
)


# ------------------------------------------------------------------ annexe 3
class NatureReclamant(StrEnum):
    """Annexe 3, section I."""

    PARTICULIER = "PARTICULIER"
    ENTREPRISE = "ENTREPRISE"
    PROFESSIONNEL = "PROFESSIONNEL"
    ASSOCIATION = "ASSOCIATION"
    AUTRE = "AUTRE"


NATURE_LABELS_FR: dict[str, str] = {
    NatureReclamant.PARTICULIER: "Particuliers",
    NatureReclamant.ENTREPRISE: "Entreprises",
    NatureReclamant.PROFESSIONNEL: "Professionnels",
    NatureReclamant.ASSOCIATION: "Associations",
    NatureReclamant.AUTRE: "Autres",
}


class Genre(StrEnum):
    """Annexe 3, section II — collected for the declaration, never for triage."""

    FEMININ = "FEMININ"
    MASCULIN = "MASCULIN"


class TrancheAge(StrEnum):
    """Annexe 3, section II."""

    A_18_25 = "A_18_25"
    A_26_60 = "A_26_60"
    PLUS_60 = "PLUS_60"


TRANCHE_LABELS_FR: dict[str, str] = {
    TrancheAge.A_18_25: "18-25 ans",
    TrancheAge.A_26_60: "26-60 ans",
    TrancheAge.PLUS_60: "Plus de 60 ans",
}


class CanalBCT(StrEnum):
    """Annexe 3, section III — the regulator's four reception buckets.

    Article 6 requires at minimum an electronic mailbox, an online form, and
    in-branch deposit; anything else (postal mail included) is the fourth line.
    """

    MESSAGERIE = "MESSAGERIE"
    FORMULAIRE_EN_LIGNE = "FORMULAIRE_EN_LIGNE"
    DEPOT_AGENCE = "DEPOT_AGENCE"
    AUTRE = "AUTRE"


CANAL_LABELS_FR: dict[str, str] = {
    CanalBCT.MESSAGERIE: "Boite de messagerie électronique",
    CanalBCT.FORMULAIRE_EN_LIGNE: "Formulaire en ligne",
    CanalBCT.DEPOT_AGENCE: "Dépôt de réclamations (agences et siège)",
    CanalBCT.AUTRE: "Autres canaux (y compris courriers postaux)",
}

#: Our internal channels mapped onto the regulator's four. Anything unmapped
#: falls into AUTRE rather than being silently dropped from the declaration.
CANAL_BCT_FOR_CHANNEL: dict[str, str] = {
    "EMAIL": CanalBCT.MESSAGERIE,
    "WEB": CanalBCT.FORMULAIRE_EN_LIGNE,
    "AGENCE": CanalBCT.DEPOT_AGENCE,
    "COURRIER": CanalBCT.AUTRE,
    "TELEPHONE": CanalBCT.AUTRE,
}


def canal_bct(channel: str | None) -> str:
    return CANAL_BCT_FOR_CHANNEL.get(channel or "", CanalBCT.AUTRE)


class SuiteReservee(StrEnum):
    """Annexe 3-IV — the two outcome columns the declaration asks for."""

    EN_COURS = "EN_COURS"
    DENOUEE_FAVEUR_CLIENT = "DENOUEE_FAVEUR_CLIENT"
    #: Not a column of its own in Annexe 3, but the bank must know it: Article 8
    #: requires that any rejection be reasoned, so a rejected complaint without
    #: a motivation is a compliance defect we can detect.
    REJETEE = "REJETEE"


# ---------------------------------------------------------------- reporting
#: Annexe 2, modifying Annexe I of circulaire n°2017-06: domain 6 (reporting
#: d'ordre général), declaration code ROGS760, "État sur les réclamations
#: reçues", annual, transmitted within 45 days of the reporting date, in XML.
REPORTING_CODE = "ROGS760"
REPORTING_INTITULE = "Etat sur les réclamations reçues"
REPORTING_PERIODICITE = "Annuelle"
REPORTING_DELAI_JOURS = 45
REPORTING_FORMAT = "XML"

#: Article 12 — the complaint-handling device is audited internally at least
#: every three years. Surfaced in the admin console as a compliance countdown.
AUDIT_INTERNE_INTERVALLE_ANS = 3
