from app.domain.deployment import assert_can_deploy, assert_can_retry, assert_can_rollback
from app.domain.enums import DeploymentStatus, Environment, LifecycleStage
from app.domain.errors import ConflictError
from app.domain.lifecycle import assert_can_approve, assert_can_promote
import pytest


def test_production_requires_approval():
    with pytest.raises(ConflictError) as exc:
        assert_can_deploy(
            approved=False,
            stage=LifecycleStage.VALIDATED,
            environment=Environment.PRODUCTION,
        )
    assert exc.value.code == "approval-required"


def test_approved_production_allowed():
    assert_can_deploy(
        approved=True,
        stage=LifecycleStage.APPROVED,
        environment=Environment.PRODUCTION,
    )


def test_staging_requires_validated():
    with pytest.raises(ConflictError):
        assert_can_deploy(
            approved=False,
            stage=LifecycleStage.DRAFT,
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


def test_approve_archived_rejected():
    with pytest.raises(ConflictError):
        assert_can_approve(approved=False, stage=LifecycleStage.ARCHIVED)


def test_promote_skips_illegal():
    with pytest.raises(ConflictError):
        assert_can_promote(current=LifecycleStage.DRAFT, target=LifecycleStage.PRODUCTION)
