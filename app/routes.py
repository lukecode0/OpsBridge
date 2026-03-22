from typing import Any
import json

from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.domain.admin import AuditEntry, DeliveryActivityEntry, QueueHealthSummary
from app.domain.intake import (
    DuplicateRequestIdentifierError,
    IntakeRequest,
    IntakeService,
    JobRunner,
    ReplayService,
    RetryService,
)


GUIDED_DEMO_SAMPLES: dict[str, dict[str, Any]] = {
    "normal-email": {
        "label": "Normal Email Intake",
        "source": "guided-demo",
        "channel": "email",
        "message": "New customer intake received through the browser demo.",
        "metadata": {"priority": "normal", "customer_tier": "standard"},
    },
    "fail-once-slack": {
        "label": "Fail Once Then Retry",
        "source": "guided-demo",
        "channel": "slack",
        "message": "Escalation event that intentionally fails once for retry demonstration.",
        "metadata": {"priority": "high", "opsbridge_failure_mode": "fail_once"},
    },
    "priority-slack": {
        "label": "Priority Slack Routing",
        "source": "guided-demo",
        "channel": "slack",
        "message": "High-priority event routed to the Slack adapter.",
        "metadata": {"priority": "urgent", "team": "operations"},
    },
}

SHOWCASE_SEED_SAMPLES: tuple[str, ...] = (
    "normal-email",
    "fail-once-slack",
    "priority-slack",
)


class IntakePayload(BaseModel):
    source: str
    external_id: str
    payload: dict[str, Any] = {}


def install_routes(app: FastAPI) -> None:
    @app.get("/")
    def public_intake(request: Request):
        settings = request.app.state.settings
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="public/intake.html",
            context={
                "submitted": request.query_params.get("submitted") == "1",
                "submitted_id": request.query_params.get("submitted_id"),
                "error": request.query_params.get("error"),
                "duplicate_id": request.query_params.get("duplicate_id"),
                "settings": settings,
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
        try:
            result = service.submit(
                IntakeRequest(
                    source=body.source,
                    external_id=body.external_id,
                    payload=body.payload,
                )
            )
        except DuplicateRequestIdentifierError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "request_id": result.request.request_id,
            "event_id": result.event.event_id,
            "delivery_attempt_id": result.delivery_attempt.attempt_id,
            "status": result.delivery_attempt.status,
        }

    @app.post("/intake")
    async def submit_public_intake(request: Request):
        form = await request.form()
        payload = {
            "message": (form.get("message") or "").strip(),
            "channel": str(form.get("channel") or "email").strip().lower() or "email",
        }
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
        external_id = str(form.get("external_id") or "")
        try:
            service.submit(
                IntakeRequest(
                    source=str(form.get("source") or ""),
                    external_id=external_id,
                    payload=payload,
                )
            )
        except DuplicateRequestIdentifierError:
            return RedirectResponse(
                url=f"/?error=duplicate-id&duplicate_id={external_id}",
                status_code=303,
            )
        return RedirectResponse(url=f"/?submitted=1&submitted_id={external_id}", status_code=303)

    @app.post("/intake/demo")
    async def submit_guided_demo(request: Request):
        form = await request.form()
        sample_id = str(form.get("sample_id") or "").strip()
        sample = GUIDED_DEMO_SAMPLES.get(sample_id)
        if sample is None:
            raise HTTPException(status_code=404, detail="Unknown demo sample.")

        repository = request.app.state.intake_repository
        external_id = _build_demo_external_id(repository.list_requests(), sample_id)
        payload = {
            "message": sample["message"],
            "channel": sample["channel"],
            **sample["metadata"],
        }
        service = IntakeService(
            repository=repository,
            jobs=request.app.state.job_dispatcher,
        )
        service.submit(
            IntakeRequest(
                source=sample["source"],
                external_id=external_id,
                payload=payload,
            )
        )
        return RedirectResponse(url=f"/?submitted=1&submitted_id={external_id}", status_code=303)

    @app.post("/admin/demo/reset")
    def reset_demo_state(request: Request):
        _reset_demo_state(request)
        return RedirectResponse(url="/admin/audit?demo_reset=1", status_code=303)

    @app.post("/admin/demo/seed")
    def seed_demo_state(request: Request):
        _reset_demo_state(request)
        _seed_showcase_requests(request)
        return RedirectResponse(url="/admin/audit?demo_seeded=1", status_code=303)

    @app.post("/admin/jobs/process")
    def process_jobs(request: Request):
        runner = JobRunner(
            repository=request.app.state.intake_repository,
            jobs=request.app.state.job_dispatcher,
            delivery_gateway=request.app.state.delivery_gateway,
        )
        runner.process_all()

        if request.headers.get("hx-request") != "true":
            request_id = request.query_params.get("request_id")
            if request_id:
                return RedirectResponse(url=f"/admin/requests/{request_id}", status_code=303)
            return RedirectResponse(url="/admin/audit", status_code=303)

        context = _build_audit_context(request)
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="admin/_audit_content.html",
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
                name="admin/_audit_content.html",
                context=context,
            )

        request_id = request.query_params.get("request_id")
        if request_id:
            return RedirectResponse(url=f"/admin/requests/{request_id}", status_code=303)
        return RedirectResponse(url="/admin/audit", status_code=303)

    @app.post("/admin/requests/{request_id}/replay")
    def replay_request(request_id: str, request: Request):
        service = ReplayService(
            repository=request.app.state.intake_repository,
            jobs=request.app.state.job_dispatcher,
        )
        service.replay_request(request_id)

        if request.headers.get("hx-request") == "true":
            context = _build_audit_context(request)
            return request.app.state.templates.TemplateResponse(
                request=request,
                name="admin/_audit_content.html",
                context=context,
            )

        return RedirectResponse(url=f"/admin/requests/{request_id}", status_code=303)

    @app.get("/admin/audit")
    def admin_audit(request: Request):
        context = _build_audit_context(request)
        context["current_page"] = "audit"
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
            name="admin/_audit_content.html",
            context=context,
        )

    @app.get("/admin/requests/{request_id}")
    def admin_request_detail(request_id: str, request: Request):
        context = _build_request_detail_context(request, request_id)
        context["current_page"] = "request_detail"
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="admin/request_detail.html",
            context=context,
        )

    @app.get("/admin/system")
    def admin_system_settings(request: Request):
        context = _build_system_context(request)
        context["current_page"] = "system"
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="admin/system.html",
            context=context,
        )

    @app.get("/admin/delivery-history")
    def admin_delivery_history(request: Request):
        context = _build_delivery_history_context(request)
        context["current_page"] = "delivery_history"
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="admin/delivery_history.html",
            context=context,
        )


def _build_audit_context(request: Request) -> dict[str, Any]:
    repository = request.app.state.intake_repository
    query = request.query_params.get("q", "").strip().lower()
    status = request.query_params.get("status", "").strip().lower()
    all_requests = repository.list_requests()
    all_latest_attempts = [
        repository.get_latest_attempt_for_request(stored_request.request_id)
        for stored_request in all_requests
    ]
    entries: list[AuditEntry] = []

    for stored_request in all_requests:
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
            AuditEntry(
                request=stored_request,
                events=repository.list_events_for_request(stored_request.request_id),
                delivery_attempts=repository.list_delivery_attempts_for_request(
                    stored_request.request_id
                ),
                latest_attempt=latest_attempt,
            )
        )

    request_attempts = {
        stored_request.request_id: repository.list_delivery_attempts_for_request(
            stored_request.request_id
        )
        for stored_request in all_requests
    }
    summary = QueueHealthSummary(
        total_requests=len(all_requests),
        queued_requests=len(
            [attempt for attempt in all_latest_attempts if attempt.status == "pending"]
        ),
        failed_requests=len(
            [attempt for attempt in all_latest_attempts if attempt.status == "failed"]
        ),
        successful_requests=len(
            [attempt for attempt in all_latest_attempts if attempt.status == "succeeded"]
        ),
        total_attempts=len(repository.delivery_attempts),
        total_events=len(repository.events),
        ever_failed_requests=len(
            [
                attempts
                for attempts in request_attempts.values()
                if any(attempt.status == "failed" for attempt in attempts)
            ]
        ),
        retried_requests=len(
            [attempts for attempts in request_attempts.values() if len(attempts) > 1]
        ),
        recovered_after_retry_requests=len(
            [
                attempts
                for request_id, attempts in request_attempts.items()
                if len(attempts) > 1
                and any(attempt.status == "failed" for attempt in attempts)
                and repository.get_latest_attempt_for_request(request_id).status == "succeeded"
            ]
        ),
        active_filters=bool(query or status),
    )

    return {
        "entries": entries,
        "q": query,
        "status": status,
        "summary": summary,
        "demo_seeded": request.query_params.get("demo_seeded") == "1",
        "demo_reset": request.query_params.get("demo_reset") == "1",
    }


def _build_request_detail_context(request: Request, request_id: str) -> dict[str, Any]:
    repository = request.app.state.intake_repository
    stored_request = repository.get_request(request_id)
    events = repository.list_events_for_request(request_id)
    attempts = repository.list_delivery_attempts_for_request(request_id)
    latest_attempt = repository.get_latest_attempt_for_request(request_id)
    return {
        "request_entry": AuditEntry(
            request=stored_request,
            events=events,
            delivery_attempts=attempts,
            latest_attempt=latest_attempt,
        )
    }


def _build_demo_external_id(existing_requests: list[Any], sample_id: str) -> str:
    prefix = sample_id.replace("-", "_")
    sample_count = sum(1 for request in existing_requests if request.external_id.startswith(prefix))
    return f"{prefix}_{sample_count + 1:03d}"


def _reset_demo_state(request: Request) -> None:
    request.app.state.intake_repository.reset()
    request.app.state.job_dispatcher.reset()
    request.app.state.delivery_gateway.reset()


def _seed_showcase_requests(request: Request) -> None:
    repository = request.app.state.intake_repository
    service = IntakeService(
        repository=repository,
        jobs=request.app.state.job_dispatcher,
    )
    for sample_id in SHOWCASE_SEED_SAMPLES:
        sample = GUIDED_DEMO_SAMPLES[sample_id]
        service.submit(
            IntakeRequest(
                source=sample["source"],
                external_id=_build_demo_external_id(repository.list_requests(), sample_id),
                payload={
                    "message": sample["message"],
                    "channel": sample["channel"],
                    **sample["metadata"],
                },
            )
        )


def _build_system_context(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    gateway = request.app.state.delivery_gateway
    return {
        "settings": settings,
        "persistence_status": request.app.state.persistence_status,
        "integration_status": [
            {
                "channel": "email",
                "provider": gateway.email_gateway.provider_name,
                "enabled": "email" in settings.enabled_channels,
                "calls": len(gateway.email_gateway.calls),
            },
            {
                "channel": "slack",
                "provider": gateway.slack_gateway.provider_name,
                "enabled": "slack" in settings.enabled_channels,
                "calls": len(gateway.slack_gateway.calls),
            },
        ],
    }


def _build_delivery_history_context(request: Request) -> dict[str, Any]:
    repository = request.app.state.intake_repository
    successful_events = [
        event for event in repository.events if event.event_type == "delivery.succeeded"
    ]
    recent_activity: list[DeliveryActivityEntry] = []
    grouped_counts: dict[tuple[str, str], int] = {}

    for event in reversed(successful_events):
        stored_request = repository.get_request(event.request_id)
        channel = str(event.payload.get("channel", "unknown"))
        provider = str(event.payload.get("provider", "unknown"))
        grouped_counts[(channel, provider)] = grouped_counts.get((channel, provider), 0) + 1
        recent_activity.append(
            DeliveryActivityEntry(
                request_id=stored_request.request_id,
                external_id=stored_request.external_id,
                channel=channel,
                provider=provider,
                delivery_id=str(event.payload.get("delivery_id", "")),
                attempt_id=str(event.payload.get("attempt_id", "")),
                created_at=event.created_at.isoformat(),
            )
        )

    grouped_activity = [
        {"channel": channel, "provider": provider, "count": count}
        for (channel, provider), count in sorted(grouped_counts.items())
    ]

    return {
        "recent_activity": recent_activity,
        "grouped_activity": grouped_activity,
        "total_deliveries": len(successful_events),
    }
