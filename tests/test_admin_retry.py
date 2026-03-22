from fastapi.testclient import TestClient

from app.factory import create_app


def test_admin_can_process_and_retry_failed_attempts() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/api/intake",
        json={
            "source": "Webhook",
            "external_id": "evt-fail",
            "payload": {"opsbridge_outcome": "fail"},
        },
    )

    process_response = client.post("/admin/jobs/process")

    assert process_response.status_code == 200
    assert "delivery.failed" in process_response.text
    assert "latest status: failed" in process_response.text
    assert "Retry Failed Attempt" in process_response.text

    failed_attempt_id = app.state.intake_repository.delivery_attempts[-1].attempt_id

    retry_response = client.post(
        f"/admin/delivery-attempts/{failed_attempt_id}/retry",
        headers={"hx-request": "true"},
    )

    assert retry_response.status_code == 200
    assert "attempt 2 is pending" in retry_response.text
    assert app.state.job_dispatcher.queued_jobs[-1]["job_name"] == "process_intake"
