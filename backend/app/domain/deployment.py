from app.domain.enums import (
    PRODUCTION_DEPLOY_STAGES,
    STAGING_DEPLOY_STAGES,
    DeploymentStatus,
    Environment,
    LifecycleStage,
)
from app.domain.errors import ConflictError

ACTIVE_DEPLOYMENT_STATUSES = {
    DeploymentStatus.REQUESTED,
    DeploymentStatus.VALIDATING,
    DeploymentStatus.DEPLOYING,
}


def assert_can_deploy(
    *,
    stage: LifecycleStage,
    environment: Environment,
) -> None:
    if stage == LifecycleStage.ARCHIVED:
        raise ConflictError(
            "archived-version",
            "Archived version cannot be deployed",
            "Choose an active version.",
        )
    if environment == Environment.PRODUCTION:
        if stage not in PRODUCTION_DEPLOY_STAGES:
            raise ConflictError(
                "invalid-stage",
                "Version is not eligible for production",
                "Promote the version to Staging before requesting a production deployment.",
            )
        return
    if stage not in STAGING_DEPLOY_STAGES:
        raise ConflictError(
            "invalid-stage",
            "Version is not eligible for staging",
            f"Stage {stage} is not allowed for staging deployments.",
        )


def assert_can_retry(*, status: DeploymentStatus) -> None:
    if status != DeploymentStatus.FAILED:
        raise ConflictError(
            "retry-not-allowed",
            "Deployment cannot be retried",
            f"Only FAILED deployments can be retried (current status: {status}).",
        )


def assert_can_rollback(
    *,
    status: DeploymentStatus,
    environment: Environment,
    has_previous: bool,
) -> None:
    if environment != Environment.PRODUCTION:
        raise ConflictError(
            "rollback-env",
            "Rollback is only supported for production",
            "Staging rollbacks are not enabled in this slice.",
        )
    if status != DeploymentStatus.SUCCEEDED:
        raise ConflictError(
            "rollback-not-allowed",
            "Unsafe rollback prevented",
            f"Only a SUCCEEDED production deployment can be rolled back (current status: {status}).",
        )
    if not has_previous:
        raise ConflictError(
            "no-previous-version",
            "Unsafe rollback prevented",
            "There is no previous succeeded production deployment to restore.",
        )
