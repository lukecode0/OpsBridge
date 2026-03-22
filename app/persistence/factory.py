from dataclasses import dataclass

from app.config import Settings
from app.domain.repositories import IntakeRepository
from app.persistence.in_memory import InMemoryIntakeRepository


@dataclass(frozen=True)
class PersistenceStatus:
    requested_backend: str
    active_backend: str
    fallback_reason: str | None = None
    database_url_configured: bool = False
    database_driver: str | None = None


def build_repository(settings: Settings) -> tuple[IntakeRepository, PersistenceStatus]:
    requested_backend = settings.persistence_backend
    if requested_backend != "database":
        return (
            InMemoryIntakeRepository(),
            PersistenceStatus(
                requested_backend=requested_backend,
                active_backend="in_memory",
                database_url_configured=bool(settings.database_url),
                database_driver=None,
            ),
        )

    database_url, driver = _resolve_database_url(settings)
    try:
        repository = _build_database_repository(database_url)
    except Exception as exc:
        return (
            InMemoryIntakeRepository(),
            PersistenceStatus(
                requested_backend=requested_backend,
                active_backend="in_memory",
                fallback_reason=str(exc),
                database_url_configured=bool(settings.database_url),
                database_driver=driver,
            ),
        )

    return (
        repository,
        PersistenceStatus(
            requested_backend=requested_backend,
            active_backend="database",
            database_url_configured=bool(settings.database_url),
            database_driver=driver,
        ),
    )


def _build_database_repository(database_url: str) -> IntakeRepository:
    from app.persistence.sqlalchemy import SQLAlchemyIntakeRepository

    return SQLAlchemyIntakeRepository.from_url(database_url)


def _resolve_database_url(settings: Settings) -> tuple[str, str]:
    if settings.database_url:
        return settings.database_url, settings.database_url.split(":", 1)[0]

    sqlite_path = settings.sqlite_path.strip() or "./opsbridge-dev.db"
    normalized_path = sqlite_path if sqlite_path.startswith("/") else f"./{sqlite_path.lstrip('./')}"
    return f"sqlite:///{normalized_path}", "sqlite"
