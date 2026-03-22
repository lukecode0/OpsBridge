from fastapi.testclient import TestClient

from app.factory import create_app


def test_delivery_history_page_renders_empty_state() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/admin/delivery-history")

    assert response.status_code == 200
    assert "Delivery History / Integration Activity" in response.text
    assert "No successful deliveries yet." in response.text


def test_delivery_history_groups_recent_activity_by_channel_and_provider() -> None:
    app = create_app()
    client = TestClient(app)

    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "delivery-email",
            "message": "Email path",
            "channel": "email",
            "metadata_json": "{}",
        },
    )
    client.post(
        "/intake",
        data={
            "source": "web-form",
            "external_id": "delivery-slack",
            "message": "Slack path",
            "channel": "slack",
            "metadata_json": "{}",
        },
    )
    client.post("/admin/jobs/process")

    response = client.get("/admin/delivery-history")

    assert response.status_code == 200
    assert "Delivery History / Integration Activity" in response.text
    assert "mock-email" in response.text
    assert "mock-slack" in response.text
    assert "delivery-email" in response.text
    assert "delivery-slack" in response.text
