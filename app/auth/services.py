"""OAuth provider별 토큰 교환 및 사용자 정보 조회."""

import httpx

from app.config import OAuthProviderConfig


def exchange_kakao_token(
    cfg: OAuthProviderConfig,
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict:
    """Kakao 인증 코드로 액세스 토큰 교환."""
    redirect_uri_to_use = cfg.redirect_uri or redirect_uri
    data = {
        "grant_type": "authorization_code",
        "client_id": cfg.client_id,
        "redirect_uri": redirect_uri_to_use,
        "code": code,
        "code_verifier": code_verifier,
        "code_challenge_method": "S256",
    }
    if cfg.client_secret:
        data["client_secret"] = cfg.client_secret

    with httpx.Client() as client:
        resp = client.post(
            cfg.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


def get_kakao_user(access_token: str) -> dict:
    """Kakao 액세스 토큰으로 사용자 정보 조회."""
    with httpx.Client() as client:
        resp = client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
    # 정규화: 우리 서비스에서 쓸 필드만
    kakao_account = data.get("kakao_account") or {}
    profile = kakao_account.get("profile") or {}
    return {
        "id": str(data.get("id", "")),
        "provider": "kakao",
        "email": kakao_account.get("email") or "",
        "name": profile.get("nickname") or kakao_account.get("name") or "",
        "picture": profile.get("profile_image_url") or "",
    }


def exchange_google_token(
    cfg: OAuthProviderConfig,
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict:
    """Google 인증 코드로 액세스 토큰 교환."""
    redirect_uri_to_use = cfg.redirect_uri or redirect_uri
    data = {
        "grant_type": "authorization_code",
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "redirect_uri": redirect_uri_to_use,
        "code": code,
        "code_verifier": code_verifier,
        "code_challenge_method": "S256",
    }
    with httpx.Client() as client:
        resp = client.post(
            cfg.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


def get_google_user(access_token: str) -> dict:
    """Google 액세스 토큰으로 사용자 정보 조회."""
    with httpx.Client() as client:
        resp = client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
    return {
        "id": str(data.get("id", "")),
        "provider": "google",
        "email": data.get("email") or "",
        "name": data.get("name") or "",
        "picture": data.get("picture") or "",
    }
