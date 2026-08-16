"""The annual declaration to the Banque Centrale de Tunisie.

Annexe 2 of circulaire n°2022-08 adds declaration **ROGS760**, "État sur les
réclamations reçues", to domain 6 of the reporting framework: annual, due within
45 days of the reporting date, transmitted as XML.

Annexe 3 fixes its four tables:

    I    répartition par nature de réclamant
    II   réclamations des particuliers par genre et par tranche d'âge
    III  répartition par canal de réception
    IV   ventilation par objet, délai moyen de réponse et suites réservées

Two rules govern everything below.

**Out-of-scope messages are excluded.** Article 2 lists six things that are not
réclamations. Counting them would overstate the bank's volume, so every query
here filters them out — and the count of what was excluded is reported
alongside, because a silent exclusion is indistinguishable from a bug.

**The delay is measured from the acknowledgement.** Article 8 starts the clock
there, not at receipt, so `délai moyen de réponse` uses `accuse_reception_at`
and counts *jours ouvrables*, matching the deadline the same complaint was held
to. Measuring in calendar days here while enforcing working days elsewhere would
produce a report that contradicts the system that generated it.
"""

from datetime import UTC, datetime
from typing import Any
from xml.etree import ElementTree as ET

from app.domain.bct import (
    CANAL_LABELS_FR,
    NATURE_LABELS_FR,
    OBJET_LABELS_FR,
    REPORTING_CODE,
    REPORTING_INTITULE,
    CanalBCT,
    Genre,
    NatureReclamant,
    ObjetBCT,
    TrancheAge,
    canal_bct,
)
from app.domain.calendar_tn import business_days_between
from app.models.complaint import CLOSED_STATUSES, Complaint, Status

#: Article 2 exclusions never reach the declaration.
IN_SCOPE = {"reglementaire.hors_perimetre": None}


def _window(year: int) -> dict[str, Any]:
    start = datetime(year, 1, 1, tzinfo=UTC)
    end = datetime(year + 1, 1, 1, tzinfo=UTC)
    return {"created_at": {"$gte": start, "$lt": end}}


async def collect(year: int) -> dict[str, Any]:
    """Gather the four Annexe 3 tables for a calendar year."""
    scope = {**_window(year), **IN_SCOPE}

    complaints = await Complaint.find(scope).to_list()
    excluded = await Complaint.find(
        {**_window(year), "reglementaire.hors_perimetre": {"$ne": None}}
    ).count()

    # ---- I. par nature de réclamant -------------------------------------
    par_nature = {nature.value: 0 for nature in NatureReclamant}
    for complaint in complaints:
        nature = complaint.claimant.nature or NatureReclamant.AUTRE
        par_nature[nature] = par_nature.get(nature, 0) + 1

    # ---- II. particuliers par genre et tranche d'âge ---------------------
    par_genre: dict[str, dict[str, int]] = {
        genre.value: {tranche.value: 0 for tranche in TrancheAge} for genre in Genre
    }
    for complaint in complaints:
        if complaint.claimant.nature != NatureReclamant.PARTICULIER:
            continue
        genre = complaint.claimant.genre
        tranche = complaint.claimant.tranche_age
        if genre in par_genre and tranche in par_genre[genre]:
            par_genre[genre][tranche] += 1

    # ---- III. par canal de réception -------------------------------------
    par_canal = {canal.value: 0 for canal in CanalBCT}
    for complaint in complaints:
        bucket = canal_bct(str(complaint.channel).upper())
        par_canal[bucket] = par_canal.get(bucket, 0) + 1

    # ---- IV. par objet, délai et suites ----------------------------------
    par_objet: dict[str, dict[str, Any]] = {
        objet.value: {"recues": 0, "jours": [], "en_cours": 0, "faveur_client": 0}
        for objet in ObjetBCT
    }
    for complaint in complaints:
        objet = complaint.reglementaire.objet_bct or ObjetBCT.AUTRES_SERVICES
        row = par_objet.setdefault(
            objet, {"recues": 0, "jours": [], "en_cours": 0, "faveur_client": 0}
        )
        row["recues"] += 1

        if complaint.status in CLOSED_STATUSES:
            start = complaint.reglementaire.accuse_reception_at or complaint.created_at
            if complaint.sla.resolved_at:
                row["jours"].append(
                    business_days_between(start, complaint.sla.resolved_at)
                )
            # "Dénouées en faveur du client" means the claim was upheld. A
            # rejection is the opposite, and a reasoned rejection is still a
            # rejection — so REJECTED is deliberately not counted here.
            if complaint.status is not Status.REJECTED:
                row["faveur_client"] += 1
        else:
            row["en_cours"] += 1

    for row in par_objet.values():
        durations = row.pop("jours")
        row["delai_moyen_jours_ouvrables"] = (
            round(sum(durations) / len(durations), 1) if durations else None
        )

    return {
        "code": REPORTING_CODE,
        "intitule": REPORTING_INTITULE,
        "annee": year,
        "total_recues": len(complaints),
        "hors_perimetre_exclues": excluded,
        "par_nature": par_nature,
        "par_genre_et_age": par_genre,
        "par_canal": par_canal,
        "par_objet": par_objet,
    }


def to_xml(report: dict[str, Any]) -> str:
    """Render the declaration as XML (Annexe 2 fixes the transmission format)."""
    root = ET.Element(
        "DeclarationReclamations",
        {"code": report["code"], "annee": str(report["annee"])},
    )
    ET.SubElement(root, "Intitule").text = report["intitule"]
    ET.SubElement(root, "TotalRecues").text = str(report["total_recues"])
    # Reported, not hidden: an exclusion nobody can see is an exclusion nobody
    # can audit.
    ET.SubElement(root, "HorsPerimetreExclues").text = str(
        report["hors_perimetre_exclues"]
    )

    nature_node = ET.SubElement(root, "RepartitionParNature")
    for code, count in report["par_nature"].items():
        ET.SubElement(
            nature_node, "Ligne",
            {"code": code, "libelle": NATURE_LABELS_FR.get(code, code)},
        ).text = str(count)

    genre_node = ET.SubElement(root, "ParticuliersParGenreEtAge")
    for genre, tranches in report["par_genre_et_age"].items():
        genre_element = ET.SubElement(genre_node, "Genre", {"code": genre})
        for tranche, count in tranches.items():
            ET.SubElement(
                genre_element, "TrancheAge", {"code": tranche}
            ).text = str(count)

    canal_node = ET.SubElement(root, "RepartitionParCanal")
    for code, count in report["par_canal"].items():
        ET.SubElement(
            canal_node, "Ligne",
            {"code": code, "libelle": CANAL_LABELS_FR.get(code, code)},
        ).text = str(count)

    objet_node = ET.SubElement(root, "VentilationParObjet")
    for code, row in report["par_objet"].items():
        element = ET.SubElement(
            objet_node, "Objet",
            {"code": code, "libelle": OBJET_LABELS_FR.get(code, code)},
        )
        ET.SubElement(element, "NombreRecues").text = str(row["recues"])
        delai = row["delai_moyen_jours_ouvrables"]
        ET.SubElement(element, "DelaiMoyenJoursOuvrables").text = (
            "" if delai is None else str(delai)
        )
        ET.SubElement(element, "EnCoursDeTraitement").text = str(row["en_cours"])
        ET.SubElement(element, "DenoueesEnFaveurDuClient").text = str(
            row["faveur_client"]
        )

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
