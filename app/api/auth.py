"""Auth API: Supabase JWT 검증 기반. 로그인은 프론트에서 Supabase Client로 처리."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.supabase_auth import verify_supabase_token

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Authorization: Bearer <Supabase access_token> 검증 후 payload 반환."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    try:
        return verify_supabase_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)) -> dict:
    """현재 로그인 사용자 정보 (Supabase JWT 검증 필요)."""
    # Supabase JWT payload: sub, email, role, user_metadata, app_metadata 등
    return {
        "sub": current_user.get("sub"),
        "email": current_user.get("email"),
        "role": current_user.get("role"),
        "user_metadata": current_user.get("user_metadata"),
        "app_metadata": current_user.get("app_metadata"),
    }
