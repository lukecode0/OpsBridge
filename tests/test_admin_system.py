from fastapi.testclient import TestClient

from app.factory import create_app


def test_admin_system_page_renders_environment_and_adapter_status() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/admin/system")

    assert response.status_code == 200
    assert "System Settings / Environment Info" in response.text
    assert "OPSBRIDGE_DELIVERY_MODE" in response.text
    assert "OPSBRIDGE_PERSISTENCE_BACKEND" in response.text
    assert "Persistence Status" in response.text
    assert "mock-email" in response.text
    assert "mock-slack" in response.text
    assert "enabled" in response.text


def test_admin_system_page_reflects_adapter_call_counts() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "system-email",
            "message": "Email path",
            "channel": "email",
            "metadata_json": "{}",
        },
    )
    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "system-slack",
            "message": "Slack path",
            "channel": "slack",
            "metadata_json": "{}",
        },
    )
    client.post("/admin/jobs/process")

    response = client.get("/admin/system")

    assert response.status_code == 200
    assert "System Settings / Environment Info" in response.text
    assert "mock-email" in response.text
    assert "mock-slack" in response.text
    assert ">1<" in response.text
