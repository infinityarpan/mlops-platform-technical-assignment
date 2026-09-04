from app.domain.enums import LifecycleStage, PROMOTE_ORDER
from app.domain.errors import ConflictError


def assert_can_approve(*, approved: bool, stage: LifecycleStage) -> None:
    if approved:
        raise ConflictError(
            "already-approved",
            "Version already approved",
            "This model version has already been approved.",
        )
    if stage == LifecycleStage.ARCHIVED:
        raise ConflictError(
            "archived-version",
            "Archived version cannot be approved",
            "Promote or restore the version before approval.",
        )


def assert_can_promote(*, current: LifecycleStage, target: LifecycleStage) -> None:
    if current == target:
        raise ConflictError(
            "noop-promotion",
            "Version already at target stage",
            f"Version is already in {target}.",
        )
    if target == LifecycleStage.ARCHIVED:
        return
    current_idx = PROMOTE_ORDER.index(current)
    target_idx = PROMOTE_ORDER.index(target)
    if target_idx < current_idx:
        raise ConflictError(
            "illegal-demotion",
            "Illegal lifecycle demotion",
            f"Cannot move from {current} to {target} without an explicit archive/restore process.",
        )
    if target_idx > current_idx + 1 and not (
        current == LifecycleStage.APPROVED and target in {LifecycleStage.STAGING, LifecycleStage.PRODUCTION}
    ):
        raise ConflictError(
            "illegal-promotion",
            "Illegal lifecycle promotion",
            f"Cannot skip from {current} to {target}.",
        )
    if target in {LifecycleStage.STAGING, LifecycleStage.PRODUCTION} and current not in {
        LifecycleStage.APPROVED,
        LifecycleStage.STAGING,
        LifecycleStage.PRODUCTION,
    }:
        raise ConflictError(
            "unapproved-promotion",
            "Version is not approved",
            "Approve the version before promoting to staging or production.",
        )
