# MLOps platform (G12)

Assignment for **Principal / Tech Lead**: a small control plane for industrial models — register versions, approve them, deploy, watch a few metrics, retry or roll back.

I did not train models. The interesting bits are the lifecycle rules, the async deploy worker, and making `docker compose up --build` actually work.

## How it is put together

The Angular app is a thin client over REST. FastAPI writes to Postgres and hands long-running deploys to Celery (Redis). The worker talks to a fake runtime so we can fail, retry and roll back without a GPU cluster.

Rules (who can go to production, what rollback is allowed) live in `backend/app/domain` and are unit-tested without the database. The UI does not reimplement them.

[Architecture notes](docs/architecture.md) · [diagram](docs/architecture-diagram.png)

Stack: Python 3.11, FastAPI, SQLAlchemy, Alembic, Postgres 16, Redis, Celery, pytest, Angular 19 + Material, Docker Compose, GitHub Actions.

Images are built from `backend/Dockerfile` and `frontend/Dockerfile`. There is no root Dockerfile; Compose is the entrypoint.

## Run it

```bash
docker compose up --build
docker compose run --rm seed
```

Postgres user/password in Compose (`mlops`/`mlops`) is for local demo only.

- UI: http://localhost:4200
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

Without Docker: copy `.env.example`, bring up Postgres + Redis, `alembic upgrade head` from `backend/`, then uvicorn + a Celery worker. `cd frontend && npm start` proxies `/api` to port 8000.

## Tests

```bash
cd backend && python -m pytest
cd frontend && npx ng test --watch=false --browsers=ChromeHeadless
```

## Trying the flows

Seed loads the pack’s pump / compressor / valve examples plus the metrics CSV.

- Inventory and version compare on Pump Failure Predictor (`1.0.0` vs `2.0.0`).
- Role dropdown → `viewer`, hit Deploy — you should see the error card (403).
- Production deploy of compressor `1.1.0` is rejected until it is approved.
- Approve, deploy, then Rollback on a succeeded production row.
- Check **Simulate failure**, deploy, Retry.
- Monitoring for `pump-failure-predictor`. Timeline is the event log.

`POST /deployments` with a repeated `Idempotency-Key` returns the original row. Unapproved production is **409**.

The toolbar sends `X-Actor-Role`. Default on the API if you omit it is `admin`, so local curl stays simple; do not ship that.

## Screenshots

![Model inventory](docs/screenshots/inventory.png)

![Deployments](docs/screenshots/deployments.png)

![Monitoring](docs/screenshots/monitoring.png)

## Docs

- [API](docs/api-design.md)
- [Tests](docs/test-strategy.md)
- [What I cut](docs/known-limitations.md)
- [ADR: async deploys](docs/adr/001-async-deployment.md)
- [ADR: uniqueness instead of Redis locks](docs/adr/002-idempotency-constraints.md)
- [Risks / follow-up](docs/risks.md)
