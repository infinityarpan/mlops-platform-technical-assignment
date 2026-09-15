from app.domain.enums import ALLOWED_STAGE_TRANSITIONS, LifecycleStage
from app.domain.errors import ConflictError


def assert_can_promote_to_staging(*, stage: LifecycleStage) -> None:
    if stage == LifecycleStage.ARCHIVED:
        raise ConflictError(
            "archived-version",
            "Archived version cannot be promoted",
            "Restore the version before promoting it to Staging.",
        )
    if stage != LifecycleStage.NONE:
        raise ConflictError(
            "already-promoted",
            "Version is already in Staging or beyond",
            f"Version is already in {stage}.",
        )


def assert_can_promote(*, current: LifecycleStage, target: LifecycleStage) -> None:
    if current == target:
        raise ConflictError(
            "noop-promotion",
            "Version already at target stage",
            f"Version is already in {target}.",
        )
    allowed = ALLOWED_STAGE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ConflictError(
            "illegal-promotion",
            "Illegal lifecycle promotion",
            f"Cannot move from {current} to {target}.",
        )
