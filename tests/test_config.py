from app.config import get_settings
from app.factory import create_app
from app.services.integrations import IntegrationRouter, RecordedEmailGateway, RecordedSlackGateway
from app.domain.intake import IntakeRequest, IntakeService, JobRunner
from app.persistence.in_memory import InMemoryIntakeRepository
from app.services.jobs import RecordedJobDispatcher


def test_get_settings_parses_delivery_configuration(monkeypatch) -> None:
    monkeypatch.setenv("OPSBRIDGE_DELIVERY_MODE", "stub")
    monkeypatch.setenv("OPSBRIDGE_DEFAULT_CHANNEL", "slack")
    monkeypatch.setenv("OPSBRIDGE_ENABLED_CHANNELS", "slack")

    settings = get_settings()

    assert settings.delivery_mode == "stub"
    assert settings.default_channel == "slack"
    assert settings.enabled_channels == ("slack",)


def test_get_settings_parses_persistence_configuration(monkeypatch) -> None:
    monkeypatch.setenv("OPSBRIDGE_PERSISTENCE_BACKEND", "database")
    monkeypatch.setenv("OPSBRIDGE_DATABASE_URL", "postgresql+psycopg://user:pass@localhost/opsbridge")
    monkeypatch.setenv("OPSBRIDGE_SQLITE_PATH", "./var/opsbridge-smoke.db")

    settings = get_settings()

    assert settings.persistence_backend == "database"
    assert settings.database_url == "postgresql+psycopg://user:pass@localhost/opsbridge"
    assert settings.sqlite_path == "./var/opsbridge-smoke.db"


def test_integration_router_falls_back_to_default_channel_when_disabled() -> None:
    repository = InMemoryIntakeRepository()
    jobs = RecordedJobDispatcher()
    gateway = IntegrationRouter(
        email_gateway=RecordedEmailGateway(provider_name="mock-email"),
        slack_gateway=RecordedSlackGateway(provider_name="mock-slack"),
        default_channel="email",
        enabled_channels=("email",),
    )
    service = IntakeService(repository, jobs)
    result = service.submit(
        IntakeRequest(
            source="webhook",
            external_id="config-fallback-1",
            payload={"message": "hello", "channel": "slack"},
        )
    )

    JobRunner(repository, jobs, gateway).process_all()

    assert gateway.email_gateway.calls == [
        (result.request.request_id, result.delivery_attempt.attempt_id)
    ]
    assert gateway.slack_gateway.calls == []
    assert repository.events[-1].payload["channel"] == "email"


def test_create_app_falls_back_to_in_memory_when_database_backend_fails(monkeypatch) -> None:
    monkeypatch.setenv("OPSBRIDGE_PERSISTENCE_BACKEND", "database")
    monkeypatch.setenv("OPSBRIDGE_DATABASE_URL", "postgresql+psycopg://localhost/opsbridge")

    def fail_database_build(_database_url):
        raise RuntimeError("Database backend unavailable for test.")

    monkeypatch.setattr("app.persistence.factory._build_database_repository", fail_database_build)

    app = create_app()

    assert app.state.persistence_status.requested_backend == "database"
    assert app.state.persistence_status.active_backend == "in_memory"
    assert app.state.persistence_status.fallback_reason == "Database backend unavailable for test."
    assert app.state.persistence_status.database_driver == "postgresql+psycopg"
    assert isinstance(app.state.intake_repository, InMemoryIntakeRepository)
