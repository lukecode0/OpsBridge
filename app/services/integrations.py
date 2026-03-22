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
    provider_name: str = "mock-email"
    calls: list[tuple[str, str]] = field(default_factory=list)

    def send(self, request: StoredRequest, attempt: DeliveryAttempt) -> DeliveryReceipt:
        self.calls.append((request.request_id, attempt.attempt_id))
        return DeliveryReceipt(
            channel=self.channel,
            provider=self.provider_name,
            delivery_id=f"email_{attempt.attempt_id}",
        )


@dataclass
class RecordedSlackGateway:
    channel: str = "slack"
    provider_name: str = "mock-slack"
    calls: list[tuple[str, str]] = field(default_factory=list)

    def send(self, request: StoredRequest, attempt: DeliveryAttempt) -> DeliveryReceipt:
        self.calls.append((request.request_id, attempt.attempt_id))
        return DeliveryReceipt(
            channel=self.channel,
            provider=self.provider_name,
            delivery_id=f"slack_{attempt.attempt_id}",
        )


@dataclass
class IntegrationRouter:
    email_gateway: RecordedEmailGateway
    slack_gateway: RecordedSlackGateway
    default_channel: str = "email"
    enabled_channels: tuple[str, ...] = ("email", "slack")

    def send(self, request: StoredRequest, attempt: DeliveryAttempt) -> DeliveryReceipt:
        channel = str(request.payload.get("channel", self.default_channel)).strip().lower()
        channel = channel or self.default_channel
        if channel not in self.enabled_channels:
            channel = self.default_channel
        if channel == "slack":
            return self.slack_gateway.send(request, attempt)
        return self.email_gateway.send(request, attempt)
