# Tests

Domain tests (`tests/unit`) have no I/O — approval, staging vs production, retry, rollback.

API tests (`tests/api`) use SQLite and a fake enqueue that runs `process_deployment` in-process, so pytest does not need Redis. They cover the assignment scenarios: two versions, promote to staging, block unstaged production deploy, deploy, rollback, idempotency key, retry, viewer 403, 422.

The worker test checks `runtime_timeout` lands on the event list.

Angular: `ApiService` HTTP tests and a smoke test that the shell renders. I did not add Playwright; Compose is how I check the broker path.

CI: ruff, pytest, headless `ng test`, `ng build`, `docker compose build` for the API and UI images.
