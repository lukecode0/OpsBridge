from dataclasses import dataclass
from typing import Protocol


class JobDispatcher(Protocol):
    def enqueue(self, job_name: str, payload: dict[str, str]) -> None:
        ...


@dataclass(frozen=True)
class IntakeRequest:
    source: str
    external_id: str


class IntakeService:
    def __init__(self, jobs: JobDispatcher) -> None:
        self.jobs = jobs

    def submit(self, request: IntakeRequest) -> dict[str, str]:
        normalized = {
            "source": request.source.strip().lower(),
            "external_id": request.external_id.strip(),
        }
        self.jobs.enqueue("process_intake", normalized)
        return normalized
