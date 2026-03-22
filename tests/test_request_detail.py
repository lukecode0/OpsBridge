from fastapi.testclient import TestClient

from app.factory import create_app


def test_request_detail_page_renders_with_lineage_and_payloads() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "detail-fail",
            "message": "Need detail",
            "metadata_json": '{"priority": "high"}',
            "force_failure": "1",
        },
    )
    client.post("/admin/jobs/process")
    failed_attempt_id = app.state.intake_repository.delivery_attempts[-1].attempt_id
    client.post(f"/admin/delivery-attempts/{failed_attempt_id}/retry")

    request_id = app.state.intake_repository.requests[0].request_id
    response = client.get(f"/admin/requests/{request_id}")

    assert response.status_code == 200
    assert "Request Detail" in response.text
    assert "Audit Timeline" in response.text
    assert "Public Intake / Homepage" in response.text
    assert "Retry Latest Failed Attempt" not in response.text
    assert "event_type" not in response.text
    assert "delivery.failed" in response.text
    assert "from att_" in response.text
    assert "priority" in response.text


def test_request_detail_page_supports_local_process_flow() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "detail-ok",
            "message": "Ready to process",
            "metadata_json": "{}",
        },
    )
    request_id = app.state.intake_repository.requests[0].request_id

    response = client.post(
        f"/admin/jobs/process?request_id={request_id}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert request_id in response.text
    assert "latest status: succeeded" in response.text


def test_request_detail_page_supports_replay_flow() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "detail-replay",
            "message": "Replay me",
            "metadata_json": "{}",
        },
    )
    client.post("/admin/jobs/process")
    request_id = app.state.intake_repository.requests[0].request_id

    replay = client.post(
        f"/admin/requests/{request_id}/replay",
        follow_redirects=True,
    )

    assert replay.status_code == 200
    assert "Replay Original Intake" in replay.text
    assert "intake.replayed" in replay.text
    assert "attempt 2 is pending" in replay.text
