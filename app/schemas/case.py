"""사건(case) API 요청/응답 스키마."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateCaseRequest(BaseModel):
    """사건 생성 요청."""

    title: str = Field(..., min_length=1, description="사건 제목")
    description: str = Field(..., min_length=1, description="사건 설명")
    issue: str = Field(..., min_length=1, description="논점")


class CreateCaseResponse(BaseModel):
    """사건 생성 응답."""

    id: str = Field(..., description="사건 ID")
    title: str = Field(..., description="사건 제목")
    description: str = Field(..., description="사건 설명")
    issue: str = Field(..., description="논점")
    status: str = Field(..., description="진행 상태")
    created_by: str = Field(..., description="생성자 user id")
    created_at: datetime = Field(..., description="생성 시각")
