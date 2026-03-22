from fastapi.testclient import TestClient

from app.factory import create_app


def test_api_intake_persists_records_and_enqueues_job() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/intake",
        json={
            "source": "  Slack ",
            "external_id": " abc-123 ",
            "payload": {"message": "hello"},
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["request_id"].startswith("req_")
    assert body["event_id"].startswith("evt_")
    assert body["delivery_attempt_id"].startswith("att_")
    assert body["status"] == "pending"

    repository = app.state.intake_repository

    assert len(repository.requests) == 1
    assert repository.requests[0].source == "slack"
    assert repository.requests[0].external_id == "abc-123"
    assert repository.requests[0].payload == {"message": "hello"}

    assert len(repository.events) == 1
    assert repository.events[0].event_type == "intake.received"
    assert repository.events[0].request_id == repository.requests[0].request_id

    assert len(repository.delivery_attempts) == 1
    assert repository.delivery_attempts[0].status == "pending"

    assert app.state.job_dispatcher.calls == [
        ("process_intake", {"request_id": repository.requests[0].request_id})
    ]
