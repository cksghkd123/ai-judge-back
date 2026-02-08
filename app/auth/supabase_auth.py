"""Supabase Auth: 백엔드에서 Supabase JWT 검증."""

import jwt

from app.config import settings

# Supabase 기본 알고리즘
SUPABASE_JWT_ALGORITHM = "HS256"


def verify_supabase_token(token: str) -> dict:
    """
    Supabase access_token(JWT) 검증 후 payload 반환.
    Dashboard > Settings > API > JWT Secret 으로 검증.
    유효하지 않으면 jwt.InvalidTokenError 등 예외.
    """
    if not settings.supabase_jwt_secret:
        raise ValueError("supabase_jwt_secret is not configured")
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=[SUPABASE_JWT_ALGORITHM],
    )
