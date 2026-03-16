"""유저 정보(User) API. 사용자의 프로필 조회."""

from fastapi import APIRouter

router = APIRouter(prefix="/user", tags=["user"])


@router.get("")
def get_user_info():
    """현재 로그인 사용자 정보 조회."""
    
    return (
        id=user.id
        name=user.display_name,
        address=user.address,
        jobs=user.jobs
    )
