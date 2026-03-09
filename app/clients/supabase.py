"""
Supabase 클라이언트 (DB + Auth 연동).

- get_supabase_for_user(access_token): anon_key + 사용자 JWT → RLS 적용 (옵션 B, 권장).
- get_supabase(): service_role_key → RLS 우회 (관리/배치용).
"""

from supabase import Client, ClientOptions, create_client

from app.config import settings

_cached_admin_client: Client | None = None


def get_supabase_for_user(access_token: str) -> Client:
    """
    요청한 사용자의 JWT로 Supabase 클라이언트 생성.
    anon_key + Authorization: Bearer <token> 이므로 DB/Storage 요청에 RLS가 적용됨 (옵션 B).
    """
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise ValueError(
            "supabase_url and supabase_anon_key must be set for user-scoped Supabase client"
        )
    options = ClientOptions(
        headers={"Authorization": f"Bearer {access_token}"},
        persist_session=False,
    )
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=options,
    )


def get_supabase() -> Client:
    """서버 전용 Supabase 클라이언트 (service_role_key). RLS 우회. 관리/배치용."""
    global _cached_admin_client
    if _cached_admin_client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError(
                "supabase_url and supabase_service_role_key must be set for server-side Supabase client"
            )
        _cached_admin_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _cached_admin_client
