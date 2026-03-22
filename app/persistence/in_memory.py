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

    def get_request(self, request_id: str) -> StoredRequest:
        for request in self.requests:
            if request.request_id == request_id:
                return request
        raise KeyError(f"Unknown request_id: {request_id}")

    def get_delivery_attempt(self, attempt_id: str) -> DeliveryAttempt:
        for attempt in self.delivery_attempts:
            if attempt.attempt_id == attempt_id:
                return attempt
        raise KeyError(f"Unknown attempt_id: {attempt_id}")

    def get_latest_attempt_for_request(self, request_id: str) -> DeliveryAttempt:
        matches = [
            attempt for attempt in self.delivery_attempts if attempt.request_id == request_id
        ]
        if not matches:
            raise KeyError(f"No attempts for request_id: {request_id}")
        return matches[-1]

    def update_delivery_attempt(self, attempt: DeliveryAttempt) -> None:
        for index, existing in enumerate(self.delivery_attempts):
            if existing.attempt_id == attempt.attempt_id:
                self.delivery_attempts[index] = attempt
                return
        raise KeyError(f"Unknown attempt_id: {attempt.attempt_id}")

    def list_requests(self) -> list[StoredRequest]:
        return list(reversed(self.requests))

    def list_events_for_request(self, request_id: str) -> list[EventRecord]:
        return [event for event in self.events if event.request_id == request_id]

    def list_delivery_attempts_for_request(self, request_id: str) -> list[DeliveryAttempt]:
        return [
            attempt for attempt in self.delivery_attempts if attempt.request_id == request_id
        ]

    def request_identifier_in_use(self, identifier: str) -> bool:
        return any(
            request.external_id == identifier or request.request_id == identifier
            for request in self.requests
        )

    def reset(self) -> None:
        self.requests.clear()
        self.events.clear()
        self.delivery_attempts.clear()
