from dataclasses import dataclass, field
from typing import Protocol

from app.domain.intake import DeliveryAttempt, StoredRequest


@dataclass(frozen=True)
class DeliveryReceipt:
    channel: str
    provider: str
    delivery_id: str


class OutboundGateway(Protocol):
    channel: str

    def send(self, request: StoredRequest, attempt: DeliveryAttempt) -> DeliveryReceipt:
        ...


@dataclass
class RecordedEmailGateway:
    channel: str = "email"
    calls: list[tuple[str, str]] = field(default_factory=list)

    def send(self, request: StoredRequest, attempt: DeliveryAttempt) -> DeliveryReceipt:
        self.calls.append((request.request_id, attempt.attempt_id))
        return DeliveryReceipt(
            channel=self.channel,
            provider="mock-email",
            delivery_id=f"email_{attempt.attempt_id}",
        )


@dataclass
class RecordedSlackGateway:
    channel: str = "slack"
    calls: list[tuple[str, str]] = field(default_factory=list)

    def send(self, request: StoredRequest, attempt: DeliveryAttempt) -> DeliveryReceipt:
        self.calls.append((request.request_id, attempt.attempt_id))
        return DeliveryReceipt(
            channel=self.channel,
            provider="mock-slack",
            delivery_id=f"slack_{attempt.attempt_id}",
        )


@dataclass
class IntegrationRouter:
    email_gateway: RecordedEmailGateway
    slack_gateway: RecordedSlackGateway

    def send(self, request: StoredRequest, attempt: DeliveryAttempt) -> DeliveryReceipt:
        channel = str(request.payload.get("channel", "email")).strip().lower() or "email"
        if channel == "slack":
            return self.slack_gateway.send(request, attempt)
        return self.email_gateway.send(request, attempt)
