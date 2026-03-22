from app.domain.intake import IntakeRequest, IntakeService, JobRunner, RetryService
from app.services.jobs import RecordedJobDispatcher
from app.services.repository import InMemoryIntakeRepository


def test_retry_attempt_tracks_previous_attempt_id() -> None:
    repository = InMemoryIntakeRepository()
    jobs = RecordedJobDispatcher()
    service = IntakeService(repository, jobs)
    initial = service.submit(
        IntakeRequest(
            source="webhook",
            external_id="lineage-1",
            payload={"opsbridge_outcome": "fail"},
        )
    )

    JobRunner(repository, jobs).process_all()
    retry = RetryService(repository, jobs).retry_attempt(initial.delivery_attempt.attempt_id)

    assert retry.previous_attempt_id == initial.delivery_attempt.attempt_id
    assert retry.attempt_number == 2
