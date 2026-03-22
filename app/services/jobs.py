from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecordedJobDispatcher:
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)
    queued_jobs: list[dict[str, Any]] = field(default_factory=list)

    def enqueue(self, job_name: str, payload: dict[str, str]) -> None:
        self.calls.append((job_name, payload))
        self.queued_jobs.append({"job_name": job_name, "payload": payload})

    def dequeue(self) -> dict[str, Any] | None:
        if not self.queued_jobs:
            return None
        return self.queued_jobs.pop(0)

    def reset(self) -> None:
        self.calls.clear()
        self.queued_jobs.clear()
