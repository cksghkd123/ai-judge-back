"""Auth 관련 요청/응답 스키마."""

from pydantic import BaseModel


class TokenRequest(BaseModel):
    """POST /auth/token 요청 body."""

    code: str
    code_verifier: str
    state: str
    provider: str  # "kakao" | "google"
    redirect_uri: str | None = None  # 토큰 교환 시 사용 (미제공 시 설정값 사용)
