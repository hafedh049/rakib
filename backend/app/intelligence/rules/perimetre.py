"""Article 2 — is this message a réclamation at all?

The circulaire defines a réclamation narrowly and then excludes six things by
name. Counting an excluded message in the annual declaration overstates the
bank's complaint volume; refusing to *handle* it would be worse. So a message
detected as out of scope is still received, acknowledged, routed and answered —
it simply carries a flag that keeps it out of the ROGS760 totals.

Detection is deliberately conservative. A false positive silently removes a real
complaint from a regulatory count, which is the one error that matters here, so
every rule below demands an explicit phrase rather than a hint. When in doubt
the message stays in scope and a human decides.
"""

from app.domain.bct import HorsPerimetre
from app.intelligence.rules.engine import find_terms

#: Ordered: the first match wins, most specific first. Terms are matched against
#: normalised, accent-folded text, so they are written the same way.
PERIMETRE_MARKERS: list[tuple[str, list[str]]] = [
    (
        HorsPerimetre.AFFAIRE_JUDICIAIRE,
        [
            "affaire en cours devant le tribunal", "procedure judiciaire en cours",
            "devant les autorites judiciaires", "procedure d'arbitrage",
            "sentence arbitrale", "decision judiciaire", "jugement rendu",
            "قضية منشورة", "حكم قضائي",
        ],
    ),
    (
        HorsPerimetre.SAISINE_MEDIATEUR,
        [
            "saisi le mediateur bancaire", "dossier chez le mediateur",
            "en cours de mediation", "organe de mediation bancaire",
            "عرضت الملف على الوسيط", "لدى الوسيط البنكي",
        ],
    ),
    (
        HorsPerimetre.LITIGE_DEJA_TRANCHE,
        [
            "reglement a l'amiable", "transaction signee avec la banque",
            "accord amiable conclu", "protocole d'accord signe",
            "تسوية بالتراضي", "اتفاق ودي",
        ],
    ),
    (
        HorsPerimetre.RAPPORT_DE_TRAVAIL,
        [
            "en tant qu'employe de la banque", "mon contrat de travail",
            "mon employeur la banque", "litige avec mon employeur",
            "ma situation salariale", "بصفتي موظفا بالبنك", "عقد شغلي",
        ],
    ),
    (
        HorsPerimetre.DEMANDE_SERVICE,
        [
            "je souhaite ouvrir un compte", "je souhaite souscrire",
            "je voudrais commander", "merci de m'ouvrir", "demande d'ouverture",
            "je souhaite obtenir un chequier", "نحب نفتح حساب", "طلب فتح حساب",
        ],
    ),
    (
        HorsPerimetre.DEMANDE_INFORMATION,
        [
            "je souhaiterais connaitre les demarches", "pourriez-vous m'indiquer",
            "je voudrais savoir comment", "demande de renseignement",
            "quelles sont les conditions", "نحب نستفسر", "طلب معلومة",
        ],
    ),
]


def detect_hors_perimetre(indexable: str) -> tuple[str | None, list[str]]:
    """Return (reason, matched terms). `None` means the message is in scope."""
    for reason, markers in PERIMETRE_MARKERS:
        matched = find_terms(indexable, markers)
        if matched:
            return reason, matched
    return None, []
