from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_DIR = Path(__file__).resolve().parent
_ENV_FILE = _APP_DIR / ".env"


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
    supabase_storage_bucket: str = ""
    """증거 파일 업로드용 Storage 버킷 이름."""


settings = Settings()
