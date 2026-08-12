"""WhatsApp channel — complete interface, no provider wired.

Tunisian claimants are reachable on WhatsApp far more reliably than by email, so
this is the first channel worth enabling. Doing so means implementing `send()`
against a Business API account; nothing else in the system changes.
"""

from typing import ClassVar

from app.notifiers.base import LoggingNotifier


class WhatsAppNotifier(LoggingNotifier):
    name: ClassVar[str] = "whatsapp"
    runs_in: ClassVar[str] = "worker"
