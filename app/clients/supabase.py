"""
Supabase 클라이언트 (DB + Auth 연동).

- 서버 전용 작업(RLS 우회, 관리)에는 service_role_key 사용.
- 사용자 권한으로 DB 접근이 필요하면 anon_key + 사용자 JWT 로 별도 클라이언트 생성 가능.
"""

from supabase import Client, create_client

from app.config import settings

_cached_client: Client | None = None


def get_supabase() -> Client:
    """서버 전용 Supabase 클라이언트 (service_role_key). RLS 우회 가능."""
    global _cached_client
    if _cached_client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError(
                "supabase_url and supabase_service_role_key must be set for server-side Supabase client"
            )
        _cached_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _cached_client
