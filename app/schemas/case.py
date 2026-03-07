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
    invite_token: str = Field(..., description="초대 토큰")


class JoinCaseRequest(BaseModel):
    """사건 참여 요청."""

    case_id: str = Field(..., description="사건 ID")
    invite_token: str = Field(..., description="초대 토큰")


class CaseListItem(BaseModel):
    """사건 목록 항목."""

    id: str = Field(..., description="사건 ID")
    title: str = Field(..., description="사건 제목")
    status: str = Field(..., description="진행 상태")
    created_at: datetime = Field(..., description="생성 시각")
    my_role: str = Field(..., description="creator | counterpart")


class CaseDetailResponse(BaseModel):
    """사건 상세 응답."""

    id: str = Field(..., description="사건 ID")
    title: str = Field(..., description="사건 제목")
    description: str = Field(..., description="사건 설명")
    issue: str = Field(..., description="논점")
    status: str = Field(..., description="진행 상태")
    created_by: str = Field(..., description="생성자 user id")
    counterpart_id: str | None = Field(None, description="상대방 user id")
    my_role: str = Field(..., description="creator | counterpart")
    created_at: datetime = Field(..., description="생성 시각")


class EvidenceCreate(BaseModel):
    """증거 제출 요청."""

    type: str = Field(..., description="text | chat | photo (Step 4에서는 text만)")
    content: str = Field(..., min_length=1, description="내용 (type=text일 때)")
    description: str | None = Field(None, description="설명 (선택)")


class EvidenceResponse(BaseModel):
    """증거 1건 응답."""

    id: str = Field(..., description="증거 ID")
    case_id: str = Field(..., description="사건 ID")
    user_id: str = Field(..., description="제출자 user id")
    type: str = Field(..., description="text | chat | photo")
    content: str | None = Field(None, description="내용")
    file_path: str | None = Field(None, description="파일 경로")
    description: str | None = Field(None, description="설명")
    created_at: datetime = Field(..., description="제출 시각")
