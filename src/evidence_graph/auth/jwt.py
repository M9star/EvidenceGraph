from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import jwt
from jwt import InvalidTokenError

from evidence_graph.config import Settings


class Role(StrEnum):
    VIEWER = "viewer"
    RESEARCHER = "researcher"
    ADMIN = "admin"


class AuthError(Exception):
    """Token missing, expired, forged, or missing the claims we require."""


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role


def verify_bearer(token: str, settings: Settings) -> Principal:
    """Verify a bearer token. We do not issue production tokens; an IdP does."""
    if settings.jwt_secret is None:
        raise AuthError("set EVIDENCEGRAPH_JWT_SECRET in .env")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer or None,
            audience=settings.jwt_audience or None,
            options={
                "require": ["sub", "exp"],
                "verify_iss": bool(settings.jwt_issuer),
                "verify_aud": bool(settings.jwt_audience),
            },
        )
    except InvalidTokenError as exc:
        raise AuthError("invalid token") from exc
    return Principal(user_id=_subject(payload), role=_role_from_claims(payload))


def mint_access_token(
    settings: Settings,
    user_id: str,
    role: str,
    ttl_s: int = 3600,
) -> str:
    """Local and test helper. Production tokens come from an identity provider."""
    if settings.jwt_secret is None:
        raise AuthError("set EVIDENCEGRAPH_JWT_SECRET in .env")
    if not user_id.strip():
        raise AuthError("user_id is required")
    try:
        Role(role)
    except ValueError as exc:
        raise AuthError(f"unknown role: {role}") from exc
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_s),
    }
    if settings.jwt_issuer:
        payload["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience
    return jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def _subject(payload: dict[str, Any]) -> str:
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise AuthError("invalid token")
    return sub


def _role_from_claims(payload: dict[str, Any]) -> Role:
    """Least privilege if the IdP omitted a role: viewer, not researcher."""
    role = payload.get("role")
    if isinstance(role, str):
        try:
            return Role(role)
        except ValueError:
            pass
    roles = payload.get("roles")
    if isinstance(roles, list):
        for item in roles:
            if isinstance(item, str):
                try:
                    return Role(item)
                except ValueError:
                    continue
    return Role.VIEWER
