from dataclasses import dataclass, field


@dataclass
class RecordedJobDispatcher:
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def enqueue(self, job_name: str, payload: dict[str, str]) -> None:
        self.calls.append((job_name, payload))
