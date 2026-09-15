from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.domain.enums import Role
from app.domain.errors import DomainError
from app.services.keycloak_auth import role_from_bearer


def db_session(db: Session = Depends(get_db)) -> Session:
    return db


def _role_from_header(x_actor_role: str) -> Role:
    try:
        return Role(x_actor_role.lower())
    except ValueError as exc:
        raise DomainError(
            "invalid-role",
            "Invalid actor role",
            f"Unknown role '{x_actor_role}'. Use viewer, approver, operator, or admin.",
            status=400,
        ) from exc


def actor_role(
    authorization: str | None = Header(default=None),
    x_actor_role: str = Header(default="admin", alias="X-Actor-Role"),
) -> Role:
    if settings.auth_mode == "oidc":
        return role_from_bearer(authorization)
    return _role_from_header(x_actor_role)
