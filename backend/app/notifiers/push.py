"""Web push channel — complete interface, no provider wired."""

from typing import ClassVar

from app.notifiers.base import LoggingNotifier


class PushNotifier(LoggingNotifier):
    name: ClassVar[str] = "push"
    runs_in: ClassVar[str] = "worker"
