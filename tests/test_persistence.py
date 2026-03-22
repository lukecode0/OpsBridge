from app.domain.repositories import IntakeRepository
from app.persistence.in_memory import InMemoryIntakeRepository


def test_in_memory_repository_exposes_domain_repository_shape() -> None:
    repository: IntakeRepository = InMemoryIntakeRepository()

    assert repository.list_requests() == []
    assert repository.list_events_for_request("missing") == []
    assert repository.list_delivery_attempts_for_request("missing") == []
