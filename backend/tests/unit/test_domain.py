from app.domain.deployment import assert_can_deploy, assert_can_retry, assert_can_rollback
from app.domain.enums import DeploymentStatus, Environment, LifecycleStage
from app.domain.errors import ConflictError
from app.domain.lifecycle import assert_can_promote, assert_can_promote_to_staging
import pytest


def test_production_requires_staging_stage():
    with pytest.raises(ConflictError) as exc:
        assert_can_deploy(
            stage=LifecycleStage.NONE,
            environment=Environment.PRODUCTION,
        )
    assert exc.value.code == "invalid-stage"


def test_staging_stage_production_allowed():
    assert_can_deploy(
        stage=LifecycleStage.STAGING,
        environment=Environment.PRODUCTION,
    )


def test_staging_deploy_allows_none():
    assert_can_deploy(
        stage=LifecycleStage.NONE,
        environment=Environment.STAGING,
    )


def test_archived_cannot_deploy():
    with pytest.raises(ConflictError):
        assert_can_deploy(
            stage=LifecycleStage.ARCHIVED,
            environment=Environment.STAGING,
        )


def test_retry_only_failed():
    with pytest.raises(ConflictError):
        assert_can_retry(status=DeploymentStatus.SUCCEEDED)
    assert_can_retry(status=DeploymentStatus.FAILED)


def test_rollback_requires_previous_succeeded_production():
    with pytest.raises(ConflictError) as exc:
        assert_can_rollback(
            status=DeploymentStatus.SUCCEEDED,
            environment=Environment.PRODUCTION,
            has_previous=False,
        )
    assert exc.value.code == "no-previous-version"
    with pytest.raises(ConflictError):
        assert_can_rollback(
            status=DeploymentStatus.FAILED,
            environment=Environment.PRODUCTION,
            has_previous=True,
        )


def test_promote_to_staging_requires_none():
    with pytest.raises(ConflictError):
        assert_can_promote_to_staging(stage=LifecycleStage.STAGING)
    assert_can_promote_to_staging(stage=LifecycleStage.NONE)


def test_promote_follows_mlflow_transitions():
    assert_can_promote(current=LifecycleStage.NONE, target=LifecycleStage.STAGING)
    assert_can_promote(current=LifecycleStage.STAGING, target=LifecycleStage.PRODUCTION)
    assert_can_promote(current=LifecycleStage.NONE, target=LifecycleStage.ARCHIVED)
    with pytest.raises(ConflictError):
        assert_can_promote(current=LifecycleStage.PRODUCTION, target=LifecycleStage.STAGING)
