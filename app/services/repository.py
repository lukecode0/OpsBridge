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
