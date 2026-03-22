from app.domain.intake import IntakeRequest, IntakeService
from app.services.jobs import RecordedJobDispatcher


def test_intake_normalizes_and_enqueues_job() -> None:
    jobs = RecordedJobDispatcher()
    service = IntakeService(jobs)

    result = service.submit(IntakeRequest(source="  Slack ", external_id="  abc-123  "))

    assert result == {"source": "slack", "external_id": "abc-123"}
    assert jobs.calls == [
        ("process_intake", {"source": "slack", "external_id": "abc-123"})
    ]
