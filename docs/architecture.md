# Architecture

Operators at a plant need somewhere to park model versions, promote them, and see whether production is healthy. This repo is that control plane, cut down so it runs on a laptop.

**Built:** registry, lifecycle, async deploy + retry/rollback, metrics read API, Angular screens, Compose, tests.

**Not built (on purpose):** real KServe, OIDC, tenants, a metrics warehouse. Those are sketched below so the cut is explicit. No Kubernetes manifests in the repo — Compose is what you run.

```
browser  →  nginx/Angular
                →  FastAPI  →  MLflow (models/versions)
                     │    └──── Pushgateway → Prometheus (inference metrics + Evidently drift)
                     │              Postgres (deployments, events)
                     │    control-plane /metrics → Prometheus (HTTP counters only)
                     └─ Redis ─ Celery worker ─ fake runtime
                              Evidently AI (drift on feature CSVs)
```

HTTP is the only contract the UI knows. Domain functions in `backend/app/domain` are used by both the API and the worker. **MLflow** holds registered models and version artifacts; **Prometheus** holds time-series operational metrics; **Evidently** computes drift from reference/current feature datasets under `data/drift/`. Postgres holds deployments and events. Redis is just how we get work off the request thread.

## Pieces

- **Angular** — inventory, version compare, deploys, monitoring, timeline. Loading / empty / error on each view.
- **FastAPI** — validation, role header, 202 on deploy, OpenAPI at `/docs`.
- **MLflow 3** — registered models, version artifacts, alias-based lifecycle (`staging`, `production`).
- **Postgres** — deployments, events.
- **Prometheus** — inference latency, errors, throughput, quality, availability; drift gauge from Evidently.
- **Evidently AI** — data drift score from reference vs current feature CSVs (`data/drift/`).
- **Celery** — `REQUESTED → VALIDATING → DEPLOYING → SUCCEEDED|FAILED`.
- **SimulatedModelRuntime** — success or `runtime_timeout`. Swap this class for a real serving client later.

## Data

A **model** keeps a stable id (`pump-failure-predictor`). A **version** has artifact URI, tags, MLflow `lifecycle_stage`, and `lock_version` for optimistic concurrency.

Stages: MLflow aliases `@staging` / `@production`, plus an archived tag on retired versions.

A **deployment** is “put this version on staging|production”. Status: `REQUESTED → VALIDATING → DEPLOYING → SUCCEEDED|FAILED`, or `ROLLED_BACK`. Events are append-only.

Metrics are pushed to **Pushgateway** (inference/demo metrics) and scraped into Prometheus; the control plane `/metrics` endpoint only exposes platform HTTP counters. Drift is computed by Evidently during seed and pushed with inference metrics. The monitoring API queries Prometheus.

## Deploy path

1. Operator posts a deploy. Production requires `Staging` or `Production` stage; otherwise 409 and we never enqueue.
2. Row is `REQUESTED`, HTTP 202, Celery task.
3. Worker re-checks rules (in case staging was revoked in the meantime), calls the runtime, writes events.
4. Retry only from `FAILED` (and clears the demo `simulate_failure` flag).
5. Rollback only from succeeded **production**, and only if an older succeeded deploy exists. We mark the current row rolled back and enqueue a restore of that previous version.

One in-flight deploy per `(model_id, environment)` — partial unique index. Client retries use `Idempotency-Key`.

If the runtime says OK and the DB commit dies, the next retry goes through VALIDATING again. A proper outbox (receipt first) is the fix; I did not add it in this window.

## Auth

**Keycloak OIDC** in Docker Compose (`AUTH_MODE=oidc`): Angular login → Bearer JWT → FastAPI validates against Keycloak JWKS and maps realm roles (`viewer`, `approver`, `operator`, `admin`).

**Header fallback** for pytest/local dev (`AUTH_MODE=header`): `X-Actor-Role` header, default `admin`.

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
