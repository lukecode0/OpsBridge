from dataclasses import dataclass
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from typing import Protocol
from uuid import uuid4


class JobDispatcher(Protocol):
    def enqueue(self, job_name: str, payload: dict[str, str]) -> None:
        ...

    def dequeue(self) -> dict[str, Any] | None:
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
    completed_at: datetime | None = None
    error_message: str | None = None
    attempt_number: int = 1


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

    def get_request(self, request_id: str) -> StoredRequest:
        ...

    def get_delivery_attempt(self, attempt_id: str) -> DeliveryAttempt:
        ...

    def get_latest_attempt_for_request(self, request_id: str) -> DeliveryAttempt:
        ...

    def update_delivery_attempt(self, attempt: DeliveryAttempt) -> None:
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


class RetryService:
    def __init__(self, repository: IntakeRepository, jobs: JobDispatcher) -> None:
        self.repository = repository
        self.jobs = jobs

    def retry_attempt(self, attempt_id: str) -> DeliveryAttempt:
        previous_attempt = self.repository.get_delivery_attempt(attempt_id)
        new_attempt = DeliveryAttempt(
            attempt_id=f"att_{uuid4().hex[:12]}",
            request_id=previous_attempt.request_id,
            target=previous_attempt.target,
            status="pending",
            created_at=datetime.now(UTC),
            attempt_number=previous_attempt.attempt_number + 1,
        )
        self.repository.save_delivery_attempt(new_attempt)
        self.jobs.enqueue("process_intake", {"request_id": previous_attempt.request_id})
        return new_attempt


class ProcessingResult:
    def __init__(self, attempt: DeliveryAttempt, event: EventRecord) -> None:
        self.attempt = attempt
        self.event = event


class JobRunner:
    def __init__(self, repository: IntakeRepository, jobs: JobDispatcher) -> None:
        self.repository = repository
        self.jobs = jobs

    def process_next(self) -> ProcessingResult | None:
        queued_job = self.jobs.dequeue()
        if queued_job is None:
            return None

        request_id = queued_job["payload"]["request_id"]
        stored_request = self.repository.get_request(request_id)
        attempt = self.repository.get_latest_attempt_for_request(request_id)
        completed_at = datetime.now(UTC)

        if self._should_fail(stored_request):
            updated_attempt = replace(
                attempt,
                status="failed",
                completed_at=completed_at,
                error_message="Intentional test failure",
            )
            event_type = "delivery.failed"
            event_payload = {
                "attempt_id": attempt.attempt_id,
                "reason": "Intentional test failure",
            }
        else:
            updated_attempt = replace(
                attempt,
                status="succeeded",
                completed_at=completed_at,
                error_message=None,
            )
            event_type = "delivery.succeeded"
            event_payload = {"attempt_id": attempt.attempt_id}

        self.repository.update_delivery_attempt(updated_attempt)
        event = EventRecord(
            event_id=f"evt_{uuid4().hex[:12]}",
            request_id=request_id,
            event_type=event_type,
            payload=event_payload,
            created_at=completed_at,
        )
        self.repository.save_event(event)
        return ProcessingResult(attempt=updated_attempt, event=event)

    def process_all(self) -> list[ProcessingResult]:
        results: list[ProcessingResult] = []
        while True:
            result = self.process_next()
            if result is None:
                return results
            results.append(result)

    def _should_fail(self, request: StoredRequest) -> bool:
        value = request.payload.get("opsbridge_outcome")
        return value == "fail"
