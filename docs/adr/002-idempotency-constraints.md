# Idempotency in Postgres, not a Redis lock

Accepted.

Two clicks, or a retried client, must not start two in-flight rollouts for the same model and environment. Redis `SET NX` expires while a deploy might still be running. A `SELECT` then `INSERT` races across API replicas.

What we have:

- Partial unique index on `(model_id, environment)` while status is `REQUESTED|VALIDATING|DEPLOYING`.
- Unique `idempotency_key`; same key returns the existing row.
- `lock_version` on versions when promoting.

Integrity errors become 409.

I did not unique `(model_id, version, environment)` forever — that would block a later re-deploy of the same pair. `SELECT FOR UPDATE` only helps inside one transaction, not after we have already returned 202.

Operators wait until the current attempt finishes before starting another to the same env. That is intentional. Cancelling a stuck in-flight row is still missing.
