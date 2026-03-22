# OpsBridge

OpsBridge is a portfolio FastAPI application that presents an operations-oriented integration console: inbound requests are accepted, normalized, routed into queued work, processed through mocked outbound adapters, and exposed through a searchable admin audit trail with retry and replay controls.

The project is intentionally browser-first. A potential employer can run it locally, submit requests from the public intake page, process them from the admin console, inspect request and delivery history, and see how the architecture is already shaped for future real integrations and PostgreSQL-backed persistence.

## Stack

- Python 3.11+
- FastAPI
- Jinja2 + HTMX for server-rendered admin interactions
- pytest
- In-memory persistence with repository interfaces shaped for future SQLAlchemy/PostgreSQL work
- Mocked email and Slack delivery adapters behind a swappable integration seam

## Local Setup

From the project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/admin/audit`
- `http://127.0.0.1:8000/admin/delivery-history`
- `http://127.0.0.1:8000/admin/system`

Run tests with:

```bash
.venv/bin/pytest
```

## Run Modes

OpsBridge supports three practical local modes:

### Default In-Memory Mode

This is the safest browser-demo mode and requires no database setup.

```bash
.venv/bin/uvicorn app.main:app --reload
```

### Local SQLite Mode

This uses the SQLAlchemy-backed repository with a local SQLite file.

Install the DB extra once:

```bash
.venv/bin/pip install -e ".[db]"
```

Then run:

```bash
OPSBRIDGE_PERSISTENCE_BACKEND=database \
OPSBRIDGE_SQLITE_PATH=./opsbridge-dev.db \
.venv/bin/uvicorn app.main:app --reload
```

### PostgreSQL Mode

If you already have PostgreSQL running locally, point OpsBridge at it directly.

```bash
OPSBRIDGE_PERSISTENCE_BACKEND=database \
OPSBRIDGE_DATABASE_URL=postgresql+psycopg://localhost:5432/opsbridge \
.venv/bin/uvicorn app.main:app --reload
```

Notes:

- When `OPSBRIDGE_DATABASE_URL` is set, PostgreSQL takes precedence over SQLite.
- When `OPSBRIDGE_PERSISTENCE_BACKEND` is not set, the app stays in in-memory mode.
- If database mode fails during startup, the app falls back to in-memory mode and reports that on `/admin/system`.

## Browser Demo Walkthrough

The quickest demo path is entirely browser-based:

1. Open the public intake page at `/`.
2. Use the guided demo cards to create:
   - a normal request
   - a fail-once request
   - an additional Slack-oriented request if you want delivery history populated
3. Open `/admin/audit`.
4. Click `Run Queued Jobs` to process the pending requests.
5. Observe one request succeed and the fail-once request move to `failed`.
6. Retry the failed request from the audit list or request detail page.
7. Run queued jobs again and observe the request recover successfully.
8. Open the request detail page to inspect payload, event history, attempt lineage, and replay controls.
9. Open `/admin/delivery-history` to see grouped outbound activity by channel/provider.
10. Open `/admin/system` to inspect the current mocked delivery configuration.

## What The App Demonstrates

- Public intake flow with normal HTML form submission
- Inbound API and browser-based request creation
- Domain-centered intake, retry, replay, and job processing logic
- Queued delivery attempts with safe retry lineage
- Searchable audit timeline with status filters
- Request detail drill-down
- Delivery-centric activity view separate from request audit history
- Environment-shaped configuration for swappable integrations

## Architecture Notes

The codebase is organized to keep domain behavior testable without live vendor access:

- `app/domain/`
  - core intake, retry, replay, and admin-facing view models
  - repository protocol definitions for future persistence adapters
- `app/persistence/`
  - current in-memory implementation of the repository contract
- `app/services/`
  - job dispatcher and mocked outbound integration adapters
- `app/templates/`
  - server-rendered public and admin UI
- `app/routes.py`
  - thin web layer that assembles domain services and renders pages

This keeps the main portfolio story clear:

- domain logic does not depend on real Slack/email services
- live integrations are optional and swappable
- persistence is abstracted early so PostgreSQL/SQLAlchemy can be introduced later without rewriting the app’s core behavior

## Current Scope

This is not yet a production deployment target. It is a polished local portfolio app focused on:

- realistic ops workflows
- auditable state transitions
- retry vs replay distinctions
- architecture that looks ready to grow

Natural next steps would be SQLAlchemy models, PostgreSQL wiring, background worker separation, and real provider adapters behind the existing seams.
