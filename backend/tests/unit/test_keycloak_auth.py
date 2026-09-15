from app.domain.enums import Role
from app.services.keycloak_auth import highest_role


def test_highest_role_prefers_admin():
    assert highest_role({"admin", "viewer"}) == Role.ADMIN
    assert highest_role({"operator", "approver"}) == Role.OPERATOR
    assert highest_role({"viewer"}) == Role.VIEWER
    assert highest_role({"other"}) is None
