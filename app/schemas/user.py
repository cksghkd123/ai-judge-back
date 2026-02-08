"""내 정보(Me) API 응답 스키마."""

from typing import Any

from pydantic import BaseModel, Field


class MeResponse(BaseModel):
    """내 정보 조회 응답. Supabase JWT payload 기반."""

    id: str = Field(..., description="사용자 ID (JWT sub)")
    email: str | None = Field(None, description="이메일")
    role: str | None = Field(None, description="역할")
    user_metadata: dict[str, Any] | None = Field(
        None,
        description="사용자 메타데이터 (display_name, avatar_url 등)",
    )
    app_metadata: dict[str, Any] | None = Field(
        None,
        description="앱 메타데이터",
    )
