"""내 정보(Me) API. 인증된 사용자의 프로필 조회."""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
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
