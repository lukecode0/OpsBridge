from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.intake import DeliveryAttempt, EventRecord, StoredRequest


class IntakeRepository(Protocol):
    def save_request(self, request: "StoredRequest") -> None:
        ...

    def save_event(self, event: "EventRecord") -> None:
        ...

    def save_delivery_attempt(self, attempt: "DeliveryAttempt") -> None:
        ...

    def get_request(self, request_id: str) -> "StoredRequest":
        ...

    def get_delivery_attempt(self, attempt_id: str) -> "DeliveryAttempt":
        ...

    def get_latest_attempt_for_request(self, request_id: str) -> "DeliveryAttempt":
        ...

    def update_delivery_attempt(self, attempt: "DeliveryAttempt") -> None:
        ...

    def list_delivery_attempts_for_request(self, request_id: str) -> list["DeliveryAttempt"]:
        ...

    def list_events_for_request(self, request_id: str) -> list["EventRecord"]:
        ...

    def list_requests(self) -> list["StoredRequest"]:
        ...

    def request_identifier_in_use(self, identifier: str) -> bool:
        ...

    def reset(self) -> None:
        ...
