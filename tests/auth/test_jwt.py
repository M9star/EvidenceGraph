from datetime import UTC, datetime, timedelta

import jwt
import pytest

from evidence_graph.auth import AuthError, Role, mint_access_token, verify_bearer
from evidence_graph.config import Settings
from tests.support import TEST_JWT_SECRET


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, jwt_secret=TEST_JWT_SECRET, **kwargs)


def test_round_trip():
    settings = _settings()
    token = mint_access_token(settings, "alice", Role.RESEARCHER.value)

    principal = verify_bearer(token, settings)

    assert principal.user_id == "alice"
    assert principal.role is Role.RESEARCHER


def test_expired_token_is_rejected():
    settings = _settings()
    token = mint_access_token(settings, "alice", Role.RESEARCHER.value, ttl_s=-1)

    with pytest.raises(AuthError):
        verify_bearer(token, settings)


def test_wrong_secret_is_rejected():
    token = mint_access_token(_settings(), "alice", Role.RESEARCHER.value)

    with pytest.raises(AuthError):
        verify_bearer(
            token, Settings(_env_file=None, jwt_secret="example-other-jwt-secret-for-tests-only")
        )


def test_missing_secret_fails_closed():
    with pytest.raises(AuthError):
        verify_bearer("anything", Settings(_env_file=None, jwt_secret=None))


def test_missing_role_defaults_to_viewer():
    settings = _settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "alice", "iat": now, "exp": now + timedelta(hours=1)},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    assert verify_bearer(token, settings).role is Role.VIEWER


def test_roles_claim_is_accepted():
    settings = _settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "alice",
            "roles": ["researcher"],
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    assert verify_bearer(token, settings).role is Role.RESEARCHER


def test_issuer_and_audience_are_checked_when_configured():
    settings = _settings(jwt_issuer="evidencegraph", jwt_audience="api")
    token = mint_access_token(settings, "alice", Role.ADMIN.value)

    assert verify_bearer(token, settings).role is Role.ADMIN
    with pytest.raises(AuthError):
        verify_bearer(token, _settings(jwt_issuer="other", jwt_audience="api"))
