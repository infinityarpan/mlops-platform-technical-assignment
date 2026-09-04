from dataclasses import dataclass


@dataclass
class RuntimeResult:
    ok: bool
    message: str
    failure_class: str | None = None


class SimulatedModelRuntime:
    """Fake serving layer. Failures are deterministic for tests."""

    def deploy(
        self,
        *,
        model_id: str,
        version: str,
        environment: str,
        simulate_failure: bool,
    ) -> RuntimeResult:
        if simulate_failure:
            return RuntimeResult(
                ok=False,
                message=f"Simulated runtime timeout deploying {model_id}:{version} to {environment}.",
                failure_class="runtime_timeout",
            )
        return RuntimeResult(
            ok=True,
            message=f"Runtime accepted {model_id}:{version} in {environment}.",
        )
