from app.domain.enums import Role
from app.domain.errors import ForbiddenError

WRITE_ROLES = {Role.OPERATOR, Role.ADMIN}
APPROVE_ROLES = {Role.APPROVER, Role.ADMIN}


def require_role(role: Role, allowed: set[Role]) -> None:
    if role not in allowed:
        raise ForbiddenError(f"Role '{role}' is not permitted for this operation.")
