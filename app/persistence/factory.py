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


def build_repository(settings: Settings) -> tuple[IntakeRepository, PersistenceStatus]:
    requested_backend = settings.persistence_backend
    if requested_backend != "database":
        return (
            InMemoryIntakeRepository(),
            PersistenceStatus(
                requested_backend=requested_backend,
                active_backend="in_memory",
                database_url_configured=bool(settings.database_url),
            ),
        )

    try:
        repository = _build_database_repository(settings)
    except Exception as exc:
        return (
            InMemoryIntakeRepository(),
            PersistenceStatus(
                requested_backend=requested_backend,
                active_backend="in_memory",
                fallback_reason=str(exc),
                database_url_configured=bool(settings.database_url),
            ),
        )

    return (
        repository,
        PersistenceStatus(
            requested_backend=requested_backend,
            active_backend="database",
            database_url_configured=bool(settings.database_url),
        ),
    )


def _build_database_repository(settings: Settings) -> IntakeRepository:
    if not settings.database_url:
        raise RuntimeError("OPSBRIDGE_DATABASE_URL is required for database persistence.")

    from app.persistence.sqlalchemy import SQLAlchemyIntakeRepository

    return SQLAlchemyIntakeRepository.from_url(settings.database_url)
