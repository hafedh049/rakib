"""Notification copy, in French.

The system notifies; it never answers a complaint on the merits. Everything
here is transactional: a receipt, a reply notice, a status change.
"""

from typing import Any

from app.events.types import EventName

SIGNATURE = "\n\n--\nRakib — Service Reclamations\nCe message est automatique."


def _ref(payload: dict[str, Any]) -> str:
    return str(payload.get("ref", ""))


def render(event: EventName, payload: dict[str, Any]) -> tuple[str, str] | None:
    """Return (subject, body) for an event, or None when it sends no mail."""
    ref = _ref(payload)

    match event:
        case EventName.COMPLAINT_CREATED:
            return (
                f"Votre reclamation {ref} a bien ete enregistree",
                f"Bonjour {payload.get('claimant_name', '')},\n\n"
                f"Nous avons bien recu votre reclamation, enregistree sous la "
                f"reference {ref}.\n\n"
                f"Objet : {payload.get('subject', '')}\n\n"
                f"Vous pouvez suivre son avancement a tout moment via ce lien "
                f"personnel :\n{payload.get('tracking_url', '')}\n\n"
                f"Conservez ce lien : il est le seul moyen d'acceder a votre "
                f"dossier sans creer de compte." + SIGNATURE,
            )

        case EventName.COMPLAINT_REPLIED:
            return (
                f"Nouvelle reponse concernant votre reclamation {ref}",
                f"Bonjour {payload.get('claimant_name', '')},\n\n"
                f"Un conseiller a repondu a votre reclamation {ref}.\n\n"
                f"{payload.get('message', '')}\n\n"
                f"Consulter le dossier :\n{payload.get('tracking_url', '')}"
                + SIGNATURE,
            )

        case EventName.COMPLAINT_RESOLVED:
            return (
                f"Votre reclamation {ref} a ete resolue",
                f"Bonjour {payload.get('claimant_name', '')},\n\n"
                f"Votre reclamation {ref} vient d'etre marquee comme resolue.\n\n"
                f"{payload.get('resolution', '')}\n\n"
                f"Consulter le dossier :\n{payload.get('tracking_url', '')}"
                + SIGNATURE,
            )

        case EventName.COMPLAINT_ASSIGNED:
            return (
                f"Nouvelle reclamation affectee : {ref}",
                f"La reclamation {ref} vous a ete affectee.\n\n"
                f"Objet : {payload.get('subject', '')}\n"
                f"Departement : {payload.get('department', '-')}",
            )

        case _:
            return None


#: Events whose mail goes to the claimant rather than to staff.
CLAIMANT_EVENTS = {
    EventName.COMPLAINT_CREATED,
    EventName.COMPLAINT_REPLIED,
    EventName.COMPLAINT_RESOLVED,
}
