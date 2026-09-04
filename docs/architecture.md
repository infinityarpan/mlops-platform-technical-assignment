# Architecture

Operators at a plant need somewhere to park model versions, promote them, and see whether production is healthy. This repo is that control plane, cut down so it runs on a laptop.

**Built:** registry, lifecycle, async deploy + retry/rollback, metrics read API, Angular screens, Compose, tests.

**Not built (on purpose):** real KServe, OIDC, tenants, a metrics warehouse. Those are sketched below so the cut is explicit. No Kubernetes manifests in the repo — Compose is what you run.

```
browser  →  nginx/Angular
                →  FastAPI  →  Postgres
                     │
                     └─ Redis ─ Celery worker ─ fake runtime
```

HTTP is the only contract the UI knows. Domain functions in `backend/app/domain` are used by both the API and the worker. Postgres is the source of truth; Redis is just how we get work off the request thread.

## Pieces

- **Angular** — inventory, version compare, deploys, monitoring, timeline. Loading / empty / error on each view.
- **FastAPI** — validation, role header, 202 on deploy, OpenAPI at `/docs`.
- **Postgres** — models, versions, deployments, events, metric samples.
- **Celery** — `REQUESTED → VALIDATING → DEPLOYING → SUCCEEDED|FAILED`.
- **SimulatedModelRuntime** — success or `runtime_timeout`. Swap this class for a real serving client later.

## Data

A **model** keeps a stable id (`pump-failure-predictor`). A **version** has artifact URI, tags, `approved`, `lifecycle_stage`, and `lock_version` for optimistic concurrency.

Stages: `DRAFT → VALIDATED → APPROVED → STAGING → PRODUCTION`, plus `ARCHIVED`.

A **deployment** is “put this version on staging|production”. Status: `REQUESTED → VALIDATING → DEPLOYING → SUCCEEDED|FAILED`, or `ROLLED_BACK`. Events are append-only.

Metrics in this demo are rows loaded from the assignment CSV, not scrapes from a live endpoint.

## Deploy path

1. Operator posts a deploy. Production requires `approved` and a sensible stage; otherwise 409 and we never enqueue.
2. Row is `REQUESTED`, HTTP 202, Celery task.
3. Worker re-checks rules (in case someone un-approved in the meantime), calls the runtime, writes events.
4. Retry only from `FAILED` (and clears the demo `simulate_failure` flag).
5. Rollback only from succeeded **production**, and only if an older succeeded deploy exists. We mark the current row rolled back and enqueue a restore of that previous version.

One in-flight deploy per `(model_id, environment)` — partial unique index. Client retries use `Idempotency-Key`.

If the runtime says OK and the DB commit dies, the next retry goes through VALIDATING again. A proper outbox (receipt first) is the fix; I did not add it in this window.

## Auth

`X-Actor-Role`: viewer / approver / operator / admin. Approvers approve; operators deploy. Trivial to spoof — fine for the exercise, not for a cluster. Artifact URIs are stored, never fetched with cloud creds here.

## Ops

JSON logs (structlog) with `correlation_id` from `X-Correlation-ID`. `/health`, `/ready`, Prometheus `/metrics`. Tracing (OTel) would be the next instrumentation pass; I did not wire the SDK.

## If this had 10k models

Keep registry in Postgres, paginate lists, index owner/stage. Do not keep high-cardinality metric points in the same OLTP tables — Timescale or daily partitions, serve rollups to the dashboard. More Celery workers, optionally a queue per env. In Kubernetes: API + worker Deployments with HPA, managed Postgres, Redis, Ingress.

Conflicting promotions: `lock_version` plus the in-flight unique index; loser gets 409.

Several runtimes: keep the adapter interface; add `runtime_type` on the version and a small factory (KServe / SageMaker / Triton).

Tenants: `tenant_id` + RLS, separate artifact prefixes. The Angular app should never see another tenant’s ids.

Schema changes in prod: expand (nullable columns) → dual write → contract. Roll the API before dropping columns.

Team split if this left the assignment: one person on the control plane (OIDC, pagination, outbox), one on the serving adapter, UI on charts/live status, platform on Grafana/SLOs. I would keep the domain package as the shared contract so those streams do not fork the lifecycle rules.

Trade-offs I rejected: synchronous deploy (hides the long bit), SQLite-only (hurts the Compose story), JWT in this window (time vs showing a role model at all). See the ADRs.
