from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from typing import Protocol
from uuid import uuid4


class JobDispatcher(Protocol):
    def enqueue(self, job_name: str, payload: dict[str, str]) -> None:
        ...


@dataclass(frozen=True)
class IntakeRequest:
    source: str
    external_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class StoredRequest:
    request_id: str
    source: str
    external_id: str
    payload: dict[str, Any]
    received_at: datetime


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    request_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class DeliveryAttempt:
    attempt_id: str
    request_id: str
    target: str
    status: str
    created_at: datetime


@dataclass(frozen=True)
class IntakeResult:
    request: StoredRequest
    event: EventRecord
    delivery_attempt: DeliveryAttempt


class IntakeRepository(Protocol):
    def save_request(self, request: StoredRequest) -> None:
        ...

    def save_event(self, event: EventRecord) -> None:
        ...

    def save_delivery_attempt(self, attempt: DeliveryAttempt) -> None:
        ...


class IntakeService:
    def __init__(self, repository: IntakeRepository, jobs: JobDispatcher) -> None:
        self.repository = repository
        self.jobs = jobs

    def submit(self, request: IntakeRequest) -> IntakeResult:
        normalized = self._normalize(request)
        now = datetime.now(UTC)
        stored_request = StoredRequest(
            request_id=f"req_{uuid4().hex[:12]}",
            source=normalized["source"],
            external_id=normalized["external_id"],
            payload=normalized["payload"],
            received_at=now,
        )
        event = EventRecord(
            event_id=f"evt_{uuid4().hex[:12]}",
            request_id=stored_request.request_id,
            event_type="intake.received",
            payload=normalized,
            created_at=now,
        )
        delivery_attempt = DeliveryAttempt(
            attempt_id=f"att_{uuid4().hex[:12]}",
            request_id=stored_request.request_id,
            target="process_intake",
            status="pending",
            created_at=now,
        )

        self.repository.save_request(stored_request)
        self.repository.save_event(event)
        self.repository.save_delivery_attempt(delivery_attempt)
        self.jobs.enqueue("process_intake", {"request_id": stored_request.request_id})

        return IntakeResult(
            request=stored_request,
            event=event,
            delivery_attempt=delivery_attempt,
        )

    def _normalize(self, request: IntakeRequest) -> dict[str, Any]:
        return {
            "source": request.source.strip().lower(),
            "external_id": request.external_id.strip(),
            "payload": request.payload,
        }
