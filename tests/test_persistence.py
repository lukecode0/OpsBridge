from app.domain.repositories import IntakeRepository
from app.domain.intake import IntakeRequest, IntakeService
from app.persistence.factory import build_repository
from app.persistence.in_memory import InMemoryIntakeRepository
from app.config import Settings
from app.services.jobs import RecordedJobDispatcher


def test_in_memory_repository_exposes_domain_repository_shape() -> None:
    repository: IntakeRepository = InMemoryIntakeRepository()

    assert repository.list_requests() == []
    assert repository.list_events_for_request("missing") == []
    assert repository.list_delivery_attempts_for_request("missing") == []


def test_sqlalchemy_repository_supports_sqlite_smoke_path(tmp_path) -> None:
    sqlite_file = tmp_path / "opsbridge-smoke.db"
    settings = Settings(
        persistence_backend="database",
        sqlite_path=str(sqlite_file),
    )

    repository, status = build_repository(settings)
    service = IntakeService(repository, RecordedJobDispatcher())
    result = service.submit(
        IntakeRequest(
            source="webhook",
            external_id="sqlite-smoke-1",
            payload={"message": "sqlite smoke"},
        )
    )

    assert status.active_backend == "database"
    assert status.database_driver == "sqlite"
    assert repository.get_request(result.request.request_id).external_id == "sqlite-smoke-1"
    assert sqlite_file.exists()
