# Async deploys on a queue

Accepted.

A deploy is not a quick INSERT. Validation plus “runtime” work can take a while. If that sat on the HTTP thread we would time out, lose `VALIDATING`/`DEPLOYING` as first-class states, and scale the API with the slowest rollout.

So `POST /deployments` writes `REQUESTED`, returns 202, and Celery runs `deployments.process`. Tests swap enqueue for a direct function call.

I looked at FastAPI `BackgroundTasks` (dies with the process, no extra consumers) and Temporal (right idea, too much for this). Sync handlers would have been shorter and would have missed the point.

Downside: the UI has to refresh to see the terminal state, and if we commit then fail to enqueue we can sit in `REQUESTED` until someone retries. An outbox would close that; SSE would make the UI nicer.
