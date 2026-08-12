"""Event bus, notifier fan-out, and the SSE broker."""

from typing import Any, ClassVar

import pytest

from app.events import bus
from app.events.dispatch import dispatch
from app.events.subscriptions import SUBSCRIPTIONS
from app.events.types import EVENT_MIN_ROLE, STREAM_KEY, Event, EventName
from app.models.user import Role
from app.notifiers.email import EmailNotifier
from app.notifiers.sse import SSEBroker
from app.notifiers.templates import render

COMPLAINTS = "/api/v1/complaints"


# --------------------------------------------------------------------------- doubles
class FakeNotifier:
    name: ClassVar[str] = "fake"
    runs_in: ClassVar[str] = "worker"
    received: ClassVar[list[tuple[EventName, dict]]] = []

    async def send(self, event: EventName, payload: dict[str, Any]) -> None:
        FakeNotifier.received.append((event, payload))


class ExplodingNotifier:
    name: ClassVar[str] = "exploding"
    runs_in: ClassVar[str] = "worker"

    async def send(self, event: EventName, payload: dict[str, Any]) -> None:
        raise RuntimeError("provider down")


class ApiOnlyNotifier:
    name: ClassVar[str] = "api-only"
    runs_in: ClassVar[str] = "api"
    received: ClassVar[list[EventName]] = []

    async def send(self, event: EventName, payload: dict[str, Any]) -> None:
        ApiOnlyNotifier.received.append(event)


@pytest.fixture(autouse=True)
def _reset_doubles():
    FakeNotifier.received.clear()
    ApiOnlyNotifier.received.clear()
    yield


@pytest.fixture
def route_to(monkeypatch):
    def _route(event: EventName, notifiers: list[type]):
        monkeypatch.setitem(SUBSCRIPTIONS, event, notifiers)

    return _route


# ------------------------------------------------------------------------- publish
async def test_publish_writes_to_the_stream():
    stream_id = await bus.publish(EventName.COMPLAINT_CREATED, {"ref": "REC-2026-00001"})
    assert stream_id is not None

    entries = await bus.get_redis().xrange(STREAM_KEY, count=100)
    assert any(fields["name"] == EventName.COMPLAINT_CREATED for _, fields in entries)


async def test_publish_never_raises_when_redis_is_down(monkeypatch):
    """A complaint being created matters more than a notification being sent."""

    def broken() -> None:
        raise ConnectionError("redis unreachable")

    monkeypatch.setattr(bus, "get_redis", broken)
    assert await bus.publish(EventName.COMPLAINT_CREATED, {"ref": "X"}) is None


async def test_event_survives_the_stream_roundtrip():
    original = Event(name=EventName.SLA_BREACHED, payload={"ref": "REC-2026-00042"})
    restored = Event.from_stream(original.to_stream())
    assert restored.name == original.name
    assert restored.payload == original.payload
    assert restored.id == original.id


async def test_payload_with_arabic_survives_serialisation():
    original = Event(
        name=EventName.COMPLAINT_CREATED, payload={"subject": "ما فماش شبكة"}
    )
    assert Event.from_stream(original.to_stream()).payload["subject"] == "ما فماش شبكة"


# ------------------------------------------------------------------------ dispatch
async def test_dispatch_delivers_to_subscribed_notifiers(route_to):
    route_to(EventName.COMPLAINT_CREATED, [FakeNotifier])
    delivered = await dispatch(EventName.COMPLAINT_CREATED, {"ref": "REC-1"})
    assert delivered == 1
    assert FakeNotifier.received[0][0] == EventName.COMPLAINT_CREATED


async def test_dispatch_respects_the_execution_context(route_to):
    """SSE only runs in the API process; email only in the worker."""
    route_to(EventName.COMPLAINT_CREATED, [FakeNotifier, ApiOnlyNotifier])

    await dispatch(EventName.COMPLAINT_CREATED, {"ref": "R"}, runs_in="worker")
    assert len(FakeNotifier.received) == 1
    assert ApiOnlyNotifier.received == []

    await dispatch(EventName.COMPLAINT_CREATED, {"ref": "R"}, runs_in="api")
    assert len(FakeNotifier.received) == 1
    assert ApiOnlyNotifier.received == [EventName.COMPLAINT_CREATED]


async def test_one_broken_channel_does_not_stop_the_others(route_to):
    route_to(EventName.COMPLAINT_CREATED, [ExplodingNotifier, FakeNotifier])
    delivered = await dispatch(EventName.COMPLAINT_CREATED, {"ref": "R"})
    assert delivered == 1
    assert FakeNotifier.received


async def test_dispatch_of_an_unsubscribed_event_is_a_no_op(route_to):
    route_to(EventName.MODEL_PROMOTED, [])
    assert await dispatch(EventName.MODEL_PROMOTED, {}) == 0


def test_every_event_has_a_subscription_entry():
    """A new event with no subscribers is almost always an oversight."""
    assert set(SUBSCRIPTIONS) == set(EventName)


def test_every_event_has_a_minimum_role():
    assert set(EVENT_MIN_ROLE) == set(EventName)


# ---------------------------------------------------------------------- SSE broker
def test_broker_delivers_to_a_permitted_subscriber():
    broker = SSEBroker()
    subscriber = broker.subscribe(role=Role.AGENT)
    delivered = broker.publish(Event(name=EventName.COMPLAINT_CREATED, payload={}))
    assert delivered == 1
    assert subscriber.queue.qsize() == 1


def test_broker_withholds_supervisor_events_from_agents():
    """An agent must not see SLA breaches or model promotions."""
    broker = SSEBroker()
    agent = broker.subscribe(role=Role.AGENT)
    supervisor = broker.subscribe(role=Role.SUPERVISOR)

    broker.publish(Event(name=EventName.SLA_BREACHED, payload={}))
    assert agent.queue.qsize() == 0
    assert supervisor.queue.qsize() == 1


def test_broker_withholds_admin_events_from_supervisors():
    broker = SSEBroker()
    supervisor = broker.subscribe(role=Role.SUPERVISOR)
    admin = broker.subscribe(role=Role.ADMIN)

    broker.publish(Event(name=EventName.MODEL_PROMOTED, payload={}))
    assert supervisor.queue.qsize() == 0
    assert admin.queue.qsize() == 1


def test_broker_drops_a_client_that_cannot_keep_up():
    broker = SSEBroker()
    broker.subscribe(role=Role.ADMIN)
    for _ in range(200):
        broker.publish(Event(name=EventName.COMPLAINT_CREATED, payload={}))
    assert broker.subscriber_count == 0


def test_unsubscribe_removes_the_client():
    broker = SSEBroker()
    subscriber = broker.subscribe(role=Role.AGENT)
    broker.unsubscribe(subscriber)
    assert broker.subscriber_count == 0


# --------------------------------------------------------------------------- email
@pytest.mark.parametrize(
    "event",
    [EventName.COMPLAINT_CREATED, EventName.COMPLAINT_REPLIED,
     EventName.COMPLAINT_RESOLVED, EventName.SLA_BREACHED, EventName.ESCALATED],
)
def test_templates_render_and_mention_the_ref(event):
    rendered = render(event, {"ref": "REC-2026-00412", "claimant_name": "Fatma"})
    assert rendered is not None
    subject, body = rendered
    assert "REC-2026-00412" in subject + body


def test_acknowledgement_carries_the_tracking_link():
    subject, body = render(
        EventName.COMPLAINT_CREATED,
        {"ref": "REC-2026-00412", "tracking_url": "https://x/portal/suivi?token=abc"},
    )
    assert "token=abc" in body
    assert "Conservez ce lien" in body


def test_claimant_events_go_to_the_claimant():
    recipients = EmailNotifier._recipients(
        EventName.COMPLAINT_CREATED,
        {"claimant_email": "fatma@example.tn", "agent_email": "agent@rakib.tn"},
    )
    assert recipients == ["fatma@example.tn"]


def test_staff_events_go_to_staff():
    recipients = EmailNotifier._recipients(
        EventName.SLA_BREACHED,
        {"claimant_email": "fatma@example.tn", "agent_email": "agent@rakib.tn"},
    )
    assert recipients == ["agent@rakib.tn"]


def test_phone_only_claimant_yields_no_recipient():
    """Normal for Tunisia — they got the link on screen instead."""
    assert EmailNotifier._recipients(
        EventName.COMPLAINT_CREATED, {"claimant_email": None}
    ) == []


async def test_email_notifier_is_silent_without_smtp_configuration():
    """Must not raise when SMTP is unset — developers run without credentials."""
    await EmailNotifier().send(
        EventName.COMPLAINT_CREATED,
        {"ref": "REC-1", "claimant_email": "fatma@example.tn"},
    )


# ------------------------------------------------------- integration with the API
async def test_creating_a_complaint_publishes_an_event(client, monkeypatch):
    published: list[tuple[EventName, dict]] = []

    async def capture(event, payload):
        published.append((event, payload))
        return "0-1"

    monkeypatch.setattr("app.services.complaint_service.publish", capture)

    await client.post(
        COMPLAINTS,
        json={
            "subject": "Facture anormale",
            "body": "Ma facture est de 187 dinars au lieu de 45 dinars ce mois-ci.",
            "claimant": {"full_name": "Fatma Ben Ali", "email": "fatma@example.tn"},
        },
    )

    assert published
    event, payload = published[0]
    assert event == EventName.COMPLAINT_CREATED
    assert payload["ref"].startswith("REC-")
    assert "token=" in payload["tracking_url"]
    assert payload["claimant_email"] == "fatma@example.tn"


async def test_correcting_a_category_publishes_the_training_signal(
    client, routed_complaint, agent_headers, monkeypatch
):
    published: list[EventName] = []

    async def capture(event, payload):
        published.append(event)
        return "0-1"

    created = await routed_complaint()
    monkeypatch.setattr("app.services.complaint_service.publish", capture)

    await client.patch(
        f"{COMPLAINTS}/{created['id']}",
        json={"category": "PAIEMENT_RECHARGE"},
        headers=agent_headers,
    )
    assert EventName.TRIAGE_CORRECTED in published


async def test_internal_notes_do_not_notify_the_claimant(
    client, routed_complaint, agent_headers, monkeypatch
):
    published: list[EventName] = []

    async def capture(event, payload):
        published.append(event)
        return "0-1"

    created = await routed_complaint()
    monkeypatch.setattr("app.services.complaint_service.publish", capture)

    await client.post(
        f"{COMPLAINTS}/{created['id']}/messages",
        json={"body": "Note interne: dossier sensible", "internal": True},
        headers=agent_headers,
    )
    assert EventName.COMPLAINT_REPLIED not in published


# ----------------------------------------------------------------------- SSE route
async def test_event_stream_requires_authentication(client):
    assert (await client.get("/api/v1/events/stream")).status_code == 401


async def test_event_stream_refuses_claimants(client, make_user, login):
    await make_user(email="c@example.tn", password="Password123!", role=Role.CLAIMANT)
    headers = await login(client, "c@example.tn", "Password123!")
    response = await client.get("/api/v1/events/stream", headers=headers)
    assert response.status_code == 403
