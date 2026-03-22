from app.domain.intake import IntakeRequest, IntakeService, JobRunner, ReplayService, RetryService
from app.services.integrations import IntegrationRouter, RecordedEmailGateway, RecordedSlackGateway
from app.services.jobs import RecordedJobDispatcher
from app.services.repository import InMemoryIntakeRepository


def test_job_runner_marks_successful_attempts() -> None:
    repository = InMemoryIntakeRepository()
    jobs = RecordedJobDispatcher()
    gateway = IntegrationRouter(RecordedEmailGateway(), RecordedSlackGateway())
    service = IntakeService(repository, jobs)
    result = service.submit(
        IntakeRequest(source="webhook", external_id="ok-1", payload={"message": "hello"})
    )

    processed = JobRunner(repository, jobs, gateway).process_all()

    assert len(processed) == 1
    assert processed[0].attempt.status == "succeeded"
    assert repository.get_delivery_attempt(result.delivery_attempt.attempt_id).status == "succeeded"
    assert repository.events[-1].event_type == "delivery.succeeded"
    assert repository.events[-1].payload["provider"] == "mock-email"
    assert gateway.email_gateway.calls == [
        (result.request.request_id, result.delivery_attempt.attempt_id)
    ]


def test_job_runner_can_fail_and_retry_attempts() -> None:
    repository = InMemoryIntakeRepository()
    jobs = RecordedJobDispatcher()
    gateway = IntegrationRouter(RecordedEmailGateway(), RecordedSlackGateway())
    service = IntakeService(repository, jobs)
    result = service.submit(
        IntakeRequest(
            source="webhook",
            external_id="fail-1",
            payload={"opsbridge_outcome": "fail"},
        )
    )

    JobRunner(repository, jobs, gateway).process_all()
    failed_attempt = repository.get_delivery_attempt(result.delivery_attempt.attempt_id)

    assert failed_attempt.status == "failed"
    assert failed_attempt.error_message == "Intentional test failure"
    assert repository.events[-1].event_type == "delivery.failed"

    retry_attempt = RetryService(repository, jobs).retry_attempt(failed_attempt.attempt_id)

    assert retry_attempt.attempt_number == 2
    assert retry_attempt.status == "pending"
    assert repository.get_latest_attempt_for_request(result.request.request_id).attempt_id == retry_attempt.attempt_id


def test_job_runner_can_fail_once_then_succeed_on_retry() -> None:
    repository = InMemoryIntakeRepository()
    jobs = RecordedJobDispatcher()
    gateway = IntegrationRouter(RecordedEmailGateway(), RecordedSlackGateway())
    service = IntakeService(repository, jobs)
    result = service.submit(
        IntakeRequest(
            source="webhook",
            external_id="fail-once-1",
            payload={"opsbridge_failure_mode": "fail_once"},
        )
    )

    JobRunner(repository, jobs, gateway).process_all()
    first_attempt = repository.get_delivery_attempt(result.delivery_attempt.attempt_id)
    assert first_attempt.status == "failed"

    retry_attempt = RetryService(repository, jobs).retry_attempt(first_attempt.attempt_id)
    JobRunner(repository, jobs, gateway).process_all()

    processed_retry = repository.get_delivery_attempt(retry_attempt.attempt_id)
    assert processed_retry.status == "succeeded"
    assert repository.events[-1].event_type == "delivery.succeeded"


def test_replay_request_records_replay_event_and_new_attempt() -> None:
    repository = InMemoryIntakeRepository()
    jobs = RecordedJobDispatcher()
    gateway = IntegrationRouter(RecordedEmailGateway(), RecordedSlackGateway())
    service = IntakeService(repository, jobs)
    result = service.submit(
        IntakeRequest(source="webhook", external_id="replay-1", payload={"message": "hello"})
    )
    JobRunner(repository, jobs, gateway).process_all()

    replay_event, replay_attempt = ReplayService(repository, jobs).replay_request(
        result.request.request_id
    )

    assert replay_event.event_type == "intake.replayed"
    assert replay_event.payload["replayed_from_attempt_id"] == result.delivery_attempt.attempt_id
    assert replay_attempt.attempt_number == 2
    assert replay_attempt.previous_attempt_id == result.delivery_attempt.attempt_id
    assert replay_attempt.status == "pending"


def test_job_runner_routes_to_slack_adapter_when_requested() -> None:
    repository = InMemoryIntakeRepository()
    jobs = RecordedJobDispatcher()
    gateway = IntegrationRouter(RecordedEmailGateway(), RecordedSlackGateway())
    service = IntakeService(repository, jobs)
    result = service.submit(
        IntakeRequest(
            source="webhook",
            external_id="slack-1",
            payload={"message": "hello", "channel": "slack"},
        )
    )

    JobRunner(repository, jobs, gateway).process_all()

    assert gateway.slack_gateway.calls == [
        (result.request.request_id, result.delivery_attempt.attempt_id)
    ]
    assert gateway.email_gateway.calls == []
    assert repository.events[-1].payload["provider"] == "mock-slack"
    assert repository.events[-1].payload["channel"] == "slack"
