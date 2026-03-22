import os

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app


@pytest.mark.skipif(
    not os.getenv("OPSBRIDGE_TEST_POSTGRES_URL"),
    reason="Set OPSBRIDGE_TEST_POSTGRES_URL to run the PostgreSQL smoke test.",
)
def test_postgres_database_mode_smoke(monkeypatch) -> None:
    monkeypatch.setenv("OPSBRIDGE_PERSISTENCE_BACKEND", "database")
    monkeypatch.setenv("OPSBRIDGE_DATABASE_URL", os.environ["OPSBRIDGE_TEST_POSTGRES_URL"])

    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/intake",
        json={
            "source": "postgres-smoke",
            "external_id": "postgres-test-smoke",
            "payload": {"message": "hello from postgres smoke"},
        },
    )

    assert response.status_code == 200
    assert app.state.persistence_status.active_backend == "database"
    assert app.state.persistence_status.database_driver == "postgresql+psycopg"

    processed = client.post("/admin/jobs/process")

    assert processed.status_code == 200
    latest = app.state.intake_repository.get_latest_attempt_for_request(
        app.state.intake_repository.list_requests()[0].request_id
    )
    assert latest.status == "succeeded"
