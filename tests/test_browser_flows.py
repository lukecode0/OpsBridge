from fastapi.testclient import TestClient

from app.factory import create_app


def test_public_intake_page_renders() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Submit an inbound request." in response.text
    assert "Open Admin Timeline" in response.text
    assert "Guided Demo" in response.text
    assert "Fail Once Then Retry" in response.text


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
    assert "Request browser-1 accepted." in response.text

    audit = client.get("/admin/audit")

    assert audit.status_code == 200
    assert "Inbound requests recorded in this demo session." in audit.text
    assert "external_id: browser-1" in audit.text
    assert "latest status: pending" in audit.text


def test_guided_demo_sample_creates_request() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/intake/demo",
        data={"sample_id": "fail-once-slack"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Request fail_once_slack_001 accepted." in response.text

    stored_request = app.state.intake_repository.requests[0]
    assert stored_request.external_id == "fail_once_slack_001"
    assert stored_request.payload["channel"] == "slack"
    assert stored_request.payload["opsbridge_failure_mode"] == "fail_once"


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

    processed_retry = client.post("/admin/jobs/process", follow_redirects=True)

    assert processed_retry.status_code == 200
    assert "latest status: succeeded" in processed_retry.text
    assert "attempt 2 is succeeded" in processed_retry.text


def test_browser_rejects_duplicate_request_identifier() -> None:
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "duplicate-1",
            "message": "First request",
            "metadata_json": "{}",
        },
        follow_redirects=True,
    )
    second = client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "duplicate-1",
            "message": "Second request",
            "metadata_json": "{}",
        },
        follow_redirects=True,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert "identifier is already in use" in second.text
    assert len(app.state.intake_repository.requests) == 1


def test_admin_audit_supports_search_and_status_filters() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "find-me",
            "message": "Normal request",
            "metadata_json": "{}",
        },
    )
    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "fail-me",
            "message": "Fail once request",
            "metadata_json": "{}",
            "force_failure": "1",
        },
    )
    client.post("/admin/jobs/process")

    failed_only = client.get("/admin/audit?status=failed")
    assert failed_only.status_code == 200
    assert "Filters are active on the timeline below." in failed_only.text
    assert "Ever Failed" in failed_only.text
    assert "external_id: fail-me" in failed_only.text
    assert "external_id: find-me" not in failed_only.text

    searched = client.get("/admin/audit?q=find-me")
    assert searched.status_code == 200
    assert "external_id: find-me" in searched.text
    assert "external_id: fail-me" not in searched.text
