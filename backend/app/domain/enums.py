from enum import StrEnum


class LifecycleStage(StrEnum):
    """MLflow model registry lifecycle expressed via aliases and tags."""

    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


STAGING_ALIAS = "staging"
PRODUCTION_ALIAS = "production"
TAG_ARCHIVED = "mlops.archived"


class DeploymentStatus(StrEnum):
    REQUESTED = "REQUESTED"
    VALIDATING = "VALIDATING"
    DEPLOYING = "DEPLOYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class Environment(StrEnum):
    STAGING = "staging"
    PRODUCTION = "production"


class Role(StrEnum):
    VIEWER = "viewer"
    APPROVER = "approver"
    OPERATOR = "operator"
    ADMIN = "admin"


PRODUCTION_DEPLOY_STAGES = {
    LifecycleStage.STAGING,
    LifecycleStage.PRODUCTION,
}

STAGING_DEPLOY_STAGES = {
    LifecycleStage.NONE,
    LifecycleStage.STAGING,
    LifecycleStage.PRODUCTION,
}

ALLOWED_STAGE_TRANSITIONS: dict[LifecycleStage, set[LifecycleStage]] = {
    LifecycleStage.NONE: {
        LifecycleStage.STAGING,
        LifecycleStage.PRODUCTION,
        LifecycleStage.ARCHIVED,
    },
    LifecycleStage.STAGING: {LifecycleStage.PRODUCTION, LifecycleStage.ARCHIVED},
    LifecycleStage.PRODUCTION: {LifecycleStage.ARCHIVED},
    LifecycleStage.ARCHIVED: set(),
}
