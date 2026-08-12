"""Outbound email over the Hostinger SMTP relay.

Send-only by design: there is no inbound mailbox and no IMAP ingestion. If SMTP
is not configured the notifier logs what it would have sent and returns, so a
developer without credentials still sees the full flow.
"""

from email.message import EmailMessage
from typing import Any, ClassVar

import aiosmtplib

from app.config import settings
from app.core.logging import get_logger
from app.events.types import EventName
from app.notifiers.templates import CLAIMANT_EVENTS, render

log = get_logger(__name__)


class EmailNotifier:
    name: ClassVar[str] = "email"
    runs_in: ClassVar[str] = "worker"

    async def send(self, event: EventName, payload: dict[str, Any]) -> None:
        rendered = render(event, payload)
        if rendered is None:
            return
        subject, body = rendered

        recipients = self._recipients(event, payload)
        if not recipients:
            log.info("email.no_recipient", event_name=str(event), ref=payload.get("ref"))
            return

        if not settings.mail_enabled:
            log.info(
                "email.disabled_would_send",
                event_name=str(event), to=recipients, subject=subject,
            )
            return

        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username or None,
                password=settings.smtp_password or None,
                start_tls=settings.smtp_starttls,
                timeout=20,
            )
        except Exception as exc:  # noqa: BLE001 — delivery failure is not fatal
            log.error(
                "email.send_failed",
                event_name=str(event), ref=payload.get("ref"), error=str(exc),
            )
            return

        log.info("email.sent", event_name=str(event), ref=payload.get("ref"),
                 recipients=len(recipients))

    @staticmethod
    def _recipients(event: EventName, payload: dict[str, Any]) -> list[str]:
        """Claimant-facing events go to the claimant; the rest go to staff."""
        if event in CLAIMANT_EVENTS:
            email = payload.get("claimant_email")
            # Phone-only claimants exist by design — they get the tracking link
            # on screen instead, so an absent address is normal, not an error.
            return [email] if email else []
        return [
            address
            for address in (
                payload.get("agent_email"),
                payload.get("supervisor_email"),
                payload.get("escalation_email"),
            )
            if address
        ]
