"""우리 서비스 JWT 발급 및 검증."""

import time

import jwt

from app.config import settings


def create_access_token(user: dict) -> str:
    """사용자 정보로 우리 서비스 JWT 생성."""
    now = int(time.time())
    expire = now + (settings.jwt_expire_minutes * 60)
    payload = {
        "sub": f"{user.get('provider', '')}:{user.get('id', '')}",
        "provider": user.get("provider", ""),
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    """JWT 검증 후 payload 반환. 유효하지 않으면 예외."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
