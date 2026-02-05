from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth.jwt import create_access_token, decode_token
from app.auth.pkce import generate_state
from app.auth.services import (
    exchange_google_token,
    exchange_kakao_token,
    get_google_user,
    get_kakao_user,
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Authorization: Bearer <jwt> 검증 후 현재 사용자 payload 반환."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    try:
        payload = decode_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class TokenRequest(BaseModel):
    code: str
    code_verifier: str
    state: str
    provider: str  # "kakao" | "google"
    redirect_uri: str | None = None  # 토큰 교환 시 사용 (미제공 시 설정값 사용)


def _get_provider_config(provider: str):
    if provider == "kakao":
        return settings.get_kakao_config()
    if provider == "google":
        return settings.get_google_config()
    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.get("/login/{provider}")
def get_login_url(
    provider: str,
    redirect_uri: str = Query(..., description="프론트 callback URL"),
    code_challenge: str = Query(..., description="PKCE code_challenge"),
    state: str | None = Query(None, description="CSRF state (미제공 시 서버에서 생성)"),
) -> dict[str, str]:
    """OAuth 인증 URL과 state 반환."""
    state = state or generate_state()
    cfg = _get_provider_config(provider)

    redirect_uri_to_use = cfg.redirect_uri or redirect_uri
    params = {
        "response_type": "code",
        "client_id": cfg.client_id,
        "redirect_uri": redirect_uri_to_use,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if provider == "google":
        params["scope"] = "openid email profile"

    auth_url = f"{cfg.authorization_url}?{urlencode(params)}"
    return {"auth_url": auth_url, "state": state}


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)) -> dict:
    """현재 로그인 사용자 정보 (JWT 검증 필요)."""
    return {
        "sub": current_user.get("sub"),
        "provider": current_user.get("provider"),
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "picture": current_user.get("picture"),
    }


@router.post("/token")
def exchange_token(body: TokenRequest) -> dict:
    """인증 코드 + code_verifier로 토큰 교환 후 사용자 정보 반환."""
    cfg = _get_provider_config(body.provider)
    redirect_uri = body.redirect_uri or (cfg.redirect_uri if hasattr(cfg, "redirect_uri") else "")

    if body.provider == "kakao":
        token_res = exchange_kakao_token(
            cfg,
            code=body.code,
            code_verifier=body.code_verifier,
            redirect_uri=redirect_uri,
        )
        access_token = token_res.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Kakao token exchange failed")
        user = get_kakao_user(access_token)
    elif body.provider == "google":
        token_res = exchange_google_token(
            cfg,
            code=body.code,
            code_verifier=body.code_verifier,
            redirect_uri=redirect_uri,
        )
        access_token = token_res.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Google token exchange failed")
        user = get_google_user(access_token)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")

    our_jwt = create_access_token(user)
    return {
        "access_token": our_jwt,
        "token_type": "bearer",
        "user": user,
    }
