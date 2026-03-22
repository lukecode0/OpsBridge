from app.domain.intake import IntakeRequest, IntakeService
from app.persistence.in_memory import InMemoryIntakeRepository
from app.services.jobs import RecordedJobDispatcher


def test_intake_persists_records_and_enqueues_job() -> None:
    repository = InMemoryIntakeRepository()
    jobs = RecordedJobDispatcher()
    service = IntakeService(repository, jobs)

    result = service.submit(
        IntakeRequest(
            source="  Slack ",
            external_id="  abc-123  ",
            payload={"message": "hello"},
        )
    )

    assert result.request.source == "slack"
    assert result.request.external_id == "abc-123"
    assert result.request.payload == {"message": "hello", "channel": "email"}
    assert result.event.request_id == result.request.request_id
    assert result.event.event_type == "intake.received"
    assert result.delivery_attempt.request_id == result.request.request_id
    assert result.delivery_attempt.target == "deliver_email"
    assert result.delivery_attempt.status == "pending"

    assert repository.requests == [result.request]
    assert repository.events == [result.event]
    assert repository.delivery_attempts == [result.delivery_attempt]
    assert jobs.calls == [
        ("process_intake", {"request_id": result.request.request_id})
    ]
