# Risks and follow-up

Things I would not ship to a real plant:

- Commit succeeded, enqueue failed → row stuck `REQUESTED`. Needs a sweeper or outbox.
- Runtime succeeded, DB commit failed → cluster and DB disagree. Store a receipt before treating the runtime as done.
- `X-Actor-Role` is not authentication. OIDC before any real cluster.
- Role header + Compose passwords are demo-only.

Safer already: unique in-flight deploy, rollback refuses if there is nothing to restore, `lock_version` on promotions.

If I had another two weeks: OIDC, pagination, outbox, a real serving client, Grafana on `/metrics`. Later: tenant_id + RLS, a TSDB for samples, expand/contract migrations as the default.

When reviewing changes I look for lifecycle rules leaking into Angular, missing tests on new transitions, and rollback skipping the previous-version check.
