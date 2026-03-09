"""Supabase Auth: 백엔드에서 Supabase JWT 검증 (ES256 + JWKS)."""

import jwt
from jwt import PyJWKClient

from app.config import settings


def verify_supabase_token(token: str) -> dict:
    """
    Supabase access_token(JWT) 검증 후 payload 반환.
    Supabase Auth JWKS 엔드포인트의 공개키로 ES256 서명 검증.
    유효하지 않으면 jwt.InvalidTokenError 등 예외.
    """
    if not settings.supabase_url:
        raise ValueError("supabase_url is required for JWKS verification")
    jwks_uri = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    jwks_client = PyJWKClient(jwks_uri)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        options={"verify_aud": False},
    )
