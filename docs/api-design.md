# API

Compose UI calls `/api/...` (nginx strips the prefix). Direct: `http://localhost:8000`. Swagger: `/docs`.

Headers worth knowing:

- `X-Actor-Role` — `viewer` | `approver` | `operator` | `admin`. If you omit it, the API currently defaults to `admin` so local scripts are less annoying.
- `X-Correlation-ID` — generated when missing.
- `Idempotency-Key` — `POST /deployments`.

| Method | Path |
|---|---|
| POST | `/models` |
| GET | `/models` |
| GET | `/models/{id}` |
| POST | `/models/{id}/versions` |
| GET | `/models/{id}/versions` |
| POST | `/models/{id}/versions/{version}/promote-to-staging` |
| POST | `/models/{id}/versions/{version}/transition-stage` |
| POST | `/deployments` (202) |
| GET | `/deployments` (`model_id`, `environment` query) |
| GET | `/deployments/{id}` |
| GET | `/deployments/{id}/events` |
| POST | `/deployments/{id}/retry` |
| POST | `/deployments/{id}/rollback` |
| GET | `/models/{id}/metrics` (Prometheus-backed) |
| GET | `/health` `/ready` `/metrics` (control-plane Prometheus scrape) |

Errors look like problem+json: `type`, `title`, `status`, `detail`, `instance`. Conflicts 409, missing 404, validation 422, role 403.
