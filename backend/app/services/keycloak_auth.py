from __future__ import annotations

import structlog
from jwt import PyJWKClient, decode
from jwt.exceptions import PyJWTError

from app.config import settings
from app.domain.enums import Role
from app.domain.errors import DomainError

logger = structlog.get_logger()

ROLE_PRIORITY = (
    Role.ADMIN,
    Role.OPERATOR,
    Role.APPROVER,
    Role.VIEWER,
)


class UnauthorizedError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__("unauthorized", "Unauthorized", detail, status=401)


_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(settings.keycloak_jwks_url)
    return _jwk_client


def reset_jwk_client() -> None:
    global _jwk_client
    _jwk_client = None


def _roles_from_claims(claims: dict) -> set[str]:
    roles: set[str] = set()
    realm_access = claims.get("realm_access") or {}
    roles.update(realm_access.get("roles") or [])
    resource_access = claims.get("resource_access") or {}
    client_roles = (resource_access.get(settings.keycloak_client_id) or {}).get("roles") or []
    roles.update(client_roles)
    return roles


def highest_role(roles: set[str]) -> Role | None:
    normalized = {role.lower() for role in roles}
    for candidate in ROLE_PRIORITY:
        if candidate.value in normalized:
            return candidate
    return None


def role_from_bearer(authorization: str | None) -> Role:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing Bearer access token.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise UnauthorizedError("Missing Bearer access token.")

    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.keycloak_issuer,
            options={"verify_aud": False},
        )
    except PyJWTError as exc:
        logger.warning("jwt_validation_failed", error=str(exc))
        raise UnauthorizedError("Invalid or expired access token.") from exc

    role = highest_role(_roles_from_claims(claims))
    if role is None:
        raise DomainError(
            "missing-role",
            "Missing platform role",
            "Token has no mlops viewer/approver/operator/admin role assigned.",
            status=403,
        )
    return role
