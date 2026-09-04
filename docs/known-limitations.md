# Limitations

Runtime is fake. Metrics are the seeded CSV, not live inference. Auth is a header. Lists are not paginated. Rollback is production-only and restores the last succeeded version — not a traffic split.

No OpenTelemetry in the running app. Seed is a Compose one-shot, not a K8s Job. Charts are cards + a short sample list, not a charting library.

pytest uses SQLite; Compose uses Postgres. The partial unique index is declared for both.
