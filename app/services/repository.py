from dataclasses import dataclass, field

from app.domain.intake import DeliveryAttempt, EventRecord, StoredRequest


@dataclass
class InMemoryIntakeRepository:
    requests: list[StoredRequest] = field(default_factory=list)
    events: list[EventRecord] = field(default_factory=list)
    delivery_attempts: list[DeliveryAttempt] = field(default_factory=list)

    def save_request(self, request: StoredRequest) -> None:
        self.requests.append(request)

    def save_event(self, event: EventRecord) -> None:
        self.events.append(event)

    def save_delivery_attempt(self, attempt: DeliveryAttempt) -> None:
        self.delivery_attempts.append(attempt)

    def list_requests(self) -> list[StoredRequest]:
        return list(reversed(self.requests))

    def list_events_for_request(self, request_id: str) -> list[EventRecord]:
        return [event for event in self.events if event.request_id == request_id]

    def list_delivery_attempts_for_request(self, request_id: str) -> list[DeliveryAttempt]:
        return [
            attempt for attempt in self.delivery_attempts if attempt.request_id == request_id
        ]
