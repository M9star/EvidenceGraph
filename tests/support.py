from evidence_graph.auth import Role, mint_access_token
from evidence_graph.config import Settings

TEST_JWT_SECRET = "example-local-jwt-secret-for-tests-only"


def auth_header(
    settings: Settings,
    user_id: str = "alice",
    role: Role = Role.RESEARCHER,
) -> dict[str, str]:
    token = mint_access_token(settings, user_id, role.value)
    return {"Authorization": f"Bearer {token}"}
