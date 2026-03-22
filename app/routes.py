from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.domain.intake import IntakeRequest, IntakeService


class IntakePayload(BaseModel):
    source: str
    external_id: str
    payload: dict[str, Any] = {}


def install_routes(app: FastAPI) -> None:
    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/intake")
    def intake(body: IntakePayload, request: Request) -> dict[str, Any]:
        service = IntakeService(
            repository=request.app.state.intake_repository,
            jobs=request.app.state.job_dispatcher,
        )
        result = service.submit(
            IntakeRequest(
                source=body.source,
                external_id=body.external_id,
                payload=body.payload,
            )
        )
        return {
            "request_id": result.request.request_id,
            "event_id": result.event.event_id,
            "delivery_attempt_id": result.delivery_attempt.attempt_id,
            "status": result.delivery_attempt.status,
        }
