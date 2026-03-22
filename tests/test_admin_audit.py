from fastapi.testclient import TestClient

from app.factory import create_app


def test_admin_audit_page_renders_timeline() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/api/intake",
        json={
            "source": "Webhook",
            "external_id": "evt-42",
            "payload": {"kind": "incident"},
        },
    )

    response = client.get("/admin/audit")

    assert response.status_code == 200
    assert "Audit Timeline" in response.text
    assert "req_" in response.text
    assert "source: webhook" in response.text
    assert "intake.received" in response.text
    assert "process_intake attempt 1 is pending" in response.text


def test_admin_audit_entries_partial_renders_empty_state() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/admin/audit/entries")

    assert response.status_code == 200
    assert "No audit entries yet" in response.text
