from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.domain.intake import IntakeRequest, IntakeService, JobRunner, RetryService


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

    @app.post("/admin/jobs/process")
    def process_jobs(request: Request):
        runner = JobRunner(
            repository=request.app.state.intake_repository,
            jobs=request.app.state.job_dispatcher,
        )
        runner.process_all()
        context = _build_audit_context(request)
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="admin/_timeline.html",
            context=context,
        )

    @app.post("/admin/delivery-attempts/{attempt_id}/retry")
    def retry_delivery_attempt(attempt_id: str, request: Request):
        service = RetryService(
            repository=request.app.state.intake_repository,
            jobs=request.app.state.job_dispatcher,
        )
        service.retry_attempt(attempt_id)

        if request.headers.get("hx-request") == "true":
            context = _build_audit_context(request)
            return request.app.state.templates.TemplateResponse(
                request=request,
                name="admin/_timeline.html",
                context=context,
            )

        return RedirectResponse(url="/admin/audit", status_code=303)

    @app.get("/admin/audit")
    def admin_audit(request: Request):
        context = _build_audit_context(request)
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="admin/audit.html",
            context=context,
        )

    @app.get("/admin/audit/entries")
    def admin_audit_entries(request: Request):
        context = _build_audit_context(request)
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="admin/_timeline.html",
            context=context,
        )


def _build_audit_context(request: Request) -> dict[str, Any]:
    repository = request.app.state.intake_repository
    entries = []

    for stored_request in repository.list_requests():
        entries.append(
            {
                "request": stored_request,
                "events": repository.list_events_for_request(stored_request.request_id),
                "delivery_attempts": repository.list_delivery_attempts_for_request(
                    stored_request.request_id
                ),
                "latest_attempt": repository.get_latest_attempt_for_request(
                    stored_request.request_id
                ),
            }
        )

    return {"entries": entries}
