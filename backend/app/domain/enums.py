from enum import StrEnum


class LifecycleStage(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


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
    LifecycleStage.APPROVED,
    LifecycleStage.STAGING,
    LifecycleStage.PRODUCTION,
}

STAGING_DEPLOY_STAGES = {
    LifecycleStage.VALIDATED,
    LifecycleStage.APPROVED,
    LifecycleStage.STAGING,
    LifecycleStage.PRODUCTION,
}

PROMOTE_ORDER = [
    LifecycleStage.DRAFT,
    LifecycleStage.VALIDATED,
    LifecycleStage.APPROVED,
    LifecycleStage.STAGING,
    LifecycleStage.PRODUCTION,
    LifecycleStage.ARCHIVED,
]
