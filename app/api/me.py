"""내 정보(Me) API. 인증된 사용자의 프로필 조회/회원 탈퇴."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.clients.supabase import get_supabase
from app.schemas.user import MeResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
def get_me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    """현재 로그인 사용자 정보 조회. Authorization: Bearer <Supabase access_token> 필요."""
    return MeResponse(
        id=current_user.get("sub") or "",
        email=current_user.get("email"),
        role=current_user.get("role"),
        user_metadata=current_user.get("user_metadata"),
        app_metadata=current_user.get("app_metadata"),
    )


@router.delete("", status_code=204)
def delete_me(current_user: dict = Depends(get_current_user)) -> None:
    """
    회원 탈퇴(계정 삭제).
    - Supabase Auth Admin API(service_role)로 현재 사용자 계정을 삭제합니다.
    - 응답: 204 No Content
    """

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase()
    try:
        supabase.auth.admin.delete_user(user_id, should_soft_delete=False)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete user")
