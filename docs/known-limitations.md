# Limitations

Runtime is fake. Operational metrics are replayed from the assignment CSV into **Pushgateway** (not live inference scrapes). Drift scores come from **Evidently** on synthetic feature CSVs under `data/drift/`. Models and versions are seeded from **JSON**. **Keycloak OIDC** protects the Docker demo; pytest/local dev still use `AUTH_MODE=header`. Lists are not paginated. Rollback is production-only and restores the last succeeded version — not a traffic split.

Model registry metadata lives in **MLflow**; Postgres stores deployments and events only.

No OpenTelemetry in the running app. Seed is a Compose one-shot, not a K8s Job. Charts are cards + a short sample list, not a charting library.

pytest uses SQLite; Compose uses Postgres. The partial unique index is declared for both.

A separate repository, **`pump-failure-mlops`**, holds the real pump-failure stack as one repo (`training/`, `serving/`, `platform/`) with no assignment JSON/CSV.
