from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.enums import Role
from app.domain.errors import DomainError


def db_session(db: Session = Depends(get_db)) -> Session:
    return db


def actor_role(x_actor_role: str = Header(default="admin", alias="X-Actor-Role")) -> Role:
    try:
        return Role(x_actor_role.lower())
    except ValueError as exc:
        raise DomainError(
            "invalid-role",
            "Invalid actor role",
            f"Unknown role '{x_actor_role}'. Use viewer, approver, operator, or admin.",
            status=400,
        ) from exc
