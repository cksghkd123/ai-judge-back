"""
외부 서비스 클라이언트.

- 서비스별로 한 파일씩 두고, get_*() 팩토리로 싱글톤/캐시된 클라이언트 제공.
- API/도메인 레이어는 여기서 제공하는 함수만 의존하도록 하면 테스트·교체가 쉬움.

추가 예시:
- Redis: clients/redis.py → get_redis()
- 이메일: clients/email.py → get_email_client()
- 스토리지(S3 등): clients/storage.py → get_storage_client()
"""

from app.clients.supabase import get_supabase, get_supabase_for_user

__all__ = ["get_supabase", "get_supabase_for_user"]
