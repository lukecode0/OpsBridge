from fastapi.testclient import TestClient

from app.factory import create_app


def test_public_intake_page_renders() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Submit an inbound request." in response.text
    assert "Open Admin Timeline" in response.text


def test_browser_submission_redirects_and_shows_admin_entry() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "browser-1",
            "message": "Hello from the browser",
            "metadata_json": '{"priority": "high"}',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Request accepted." in response.text

    audit = client.get("/admin/audit")

    assert audit.status_code == 200
    assert "external_id: browser-1" in audit.text
    assert "latest status: pending" in audit.text


def test_browser_admin_actions_work_without_htmx() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "browser-fail",
            "message": "Please fail",
            "metadata_json": "{}",
            "force_failure": "1",
        },
    )

    processed = client.post("/admin/jobs/process", follow_redirects=True)

    assert processed.status_code == 200
    assert "latest status: failed" in processed.text
    assert "Retry Failed Attempt" in processed.text

    failed_attempt_id = app.state.intake_repository.delivery_attempts[-1].attempt_id
    retried = client.post(
        f"/admin/delivery-attempts/{failed_attempt_id}/retry",
        follow_redirects=True,
    )

    assert retried.status_code == 200
    assert "attempt 2 is pending" in retried.text
    assert f"from {failed_attempt_id}" in retried.text
