from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_DIR = Path(__file__).resolve().parent
_ENV_FILE = _APP_DIR / ".env"


class OAuthProviderConfig:
    """레거시: Supabase Auth 전환 후 제거 가능."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_url: str,
        token_url: str,
        userinfo_url: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.userinfo_url = userinfo_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase (Auth + DB)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    """프론트/공개용. 백엔드에서 사용자 권한으로 호출할 때."""
    supabase_service_role_key: str = ""
    """서버 전용. RLS 우회·관리 작업용. 노출 금지."""
    supabase_jwt_secret: str = ""
    """JWT 검증용 (Dashboard > Settings > API > JWT Secret)."""

    # 레거시 OAuth (Supabase Auth 사용 시 미사용, 추후 제거 가능)
    kakao_client_id: str = ""
    kakao_client_secret: str = ""
    kakao_redirect_uri: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    def get_kakao_config(self) -> OAuthProviderConfig:
        return OAuthProviderConfig(
            client_id=self.kakao_client_id,
            client_secret=self.kakao_client_secret,
            redirect_uri=self.kakao_redirect_uri,
            authorization_url="https://kauth.kakao.com/oauth/authorize",
            token_url="https://kauth.kakao.com/oauth/token",
            userinfo_url="https://kapi.kakao.com/v2/user/me",
        )

    def get_google_config(self) -> OAuthProviderConfig:
        return OAuthProviderConfig(
            client_id=self.google_client_id,
            client_secret=self.google_client_secret,
            redirect_uri=self.google_redirect_uri,
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
        )


settings = Settings()
