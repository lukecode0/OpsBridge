from typing import Any
import json

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.domain.intake import IntakeRequest, IntakeService, JobRunner, RetryService


class IntakePayload(BaseModel):
    source: str
    external_id: str
    payload: dict[str, Any] = {}


def install_routes(app: FastAPI) -> None:
    @app.get("/")
    def public_intake(request: Request):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="public/intake.html",
            context={
                "submitted": request.query_params.get("submitted") == "1",
                "error": request.query_params.get("error"),
            },
        )

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

    @app.post("/intake")
    async def submit_public_intake(request: Request):
        form = await request.form()
        payload = {"message": (form.get("message") or "").strip()}
        force_failure = form.get("force_failure")

        metadata_raw = (form.get("metadata_json") or "").strip()
        if metadata_raw:
            try:
                payload.update(json.loads(metadata_raw))
            except json.JSONDecodeError:
                return RedirectResponse(url="/?error=invalid-json", status_code=303)

        if force_failure:
            payload["opsbridge_failure_mode"] = "fail_once"

        service = IntakeService(
            repository=request.app.state.intake_repository,
            jobs=request.app.state.job_dispatcher,
        )
        service.submit(
            IntakeRequest(
                source=str(form.get("source") or ""),
                external_id=str(form.get("external_id") or ""),
                payload=payload,
            )
        )
        return RedirectResponse(url="/?submitted=1", status_code=303)

    @app.post("/admin/jobs/process")
    def process_jobs(request: Request):
        runner = JobRunner(
            repository=request.app.state.intake_repository,
            jobs=request.app.state.job_dispatcher,
        )
        runner.process_all()

        if request.headers.get("hx-request") != "true":
            return RedirectResponse(url="/admin/audit", status_code=303)

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
    query = request.query_params.get("q", "").strip().lower()
    status = request.query_params.get("status", "").strip().lower()
    entries = []

    for stored_request in repository.list_requests():
        latest_attempt = repository.get_latest_attempt_for_request(stored_request.request_id)
        if status and latest_attempt.status != status:
            continue

        searchable = " ".join(
            [
                stored_request.request_id,
                stored_request.source,
                stored_request.external_id,
                json.dumps(stored_request.payload, sort_keys=True),
            ]
        ).lower()
        if query and query not in searchable:
            continue

        entries.append(
            {
                "request": stored_request,
                "events": repository.list_events_for_request(stored_request.request_id),
                "delivery_attempts": repository.list_delivery_attempts_for_request(
                    stored_request.request_id
                ),
                "latest_attempt": latest_attempt,
            }
        )

    return {"entries": entries, "q": query, "status": status}
