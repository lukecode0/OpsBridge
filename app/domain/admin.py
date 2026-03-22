from dataclasses import dataclass

from app.domain.intake import DeliveryAttempt, EventRecord, StoredRequest


@dataclass(frozen=True)
class AuditEntry:
    request: StoredRequest
    events: list[EventRecord]
    delivery_attempts: list[DeliveryAttempt]
    latest_attempt: DeliveryAttempt


@dataclass(frozen=True)
class QueueHealthSummary:
    total_requests: int
    queued_requests: int
    failed_requests: int
    successful_requests: int
    total_attempts: int
    total_events: int
    ever_failed_requests: int
    retried_requests: int
    recovered_after_retry_requests: int
    active_filters: bool


@dataclass(frozen=True)
class DeliveryActivityEntry:
    request_id: str
    external_id: str
    channel: str
    provider: str
    delivery_id: str
    attempt_id: str
    created_at: str
