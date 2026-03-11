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


class CasePreviewResponse(BaseModel):
    """사건 미리보기 (초대 링크용)"""

    id: str = Field(..., description="사건 ID")
    title: str = Field(..., description="사건 제목")
    description: str = Field(..., description="사건 설명")
    issue: str = Field(..., description="논점")
    status: str = Field(..., description="진행 상태")
    created_at: datetime = Field(..., description="생성 시각")


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
    invite_token: str = Field(..., description="초대 토큰")
    creator_evidence_complete: bool = Field(
        False, description="원고(생성자) 쪽 증거 제출 완료 여부"
    )
    counterparty_evidence_complete: bool = Field(
        False, description="피고(상대방) 쪽 증거 제출 완료 여부"
    )
    creator_rebuttal_complete: bool = Field(
        False, description="원고(생성자) 쪽 반박 완료 여부"
    )
    counterparty_rebuttal_complete: bool = Field(
        False, description="피고(상대방) 쪽 반박 완료 여부"
    )


class EvidenceCreate(BaseModel):
    """증거 제출 요청."""

    type: str = Field(..., description="text | chat | photo")
    content: str | None = Field(
        None,
        description="type=text일 때 본문(필수), type=chat|photo일 때 설명(선택)",
    )


class EvidenceResponse(BaseModel):
    """증거 1건 응답."""

    id: str = Field(..., description="증거 ID")
    case_id: str = Field(..., description="사건 ID")
    user_id: str = Field(..., description="제출자 user id")
    type: str = Field(..., description="text | chat | photo")
    content: str | None = Field(None, description="내용 (text=본문, photo/chat=설명)")
    file_path: str | None = Field(None, description="파일 경로")
    created_at: datetime = Field(..., description="제출 시각")


class RebuttalRequest(BaseModel):
    """반박 제출/수정 요청."""

    accepted: bool = Field(..., description="해당 증거 수용 여부")
    rebuttal: str | None = Field(None, description="반박 내용 (선택)")


class RebuttalResponse(BaseModel):
    """반박 1건 응답."""

    id: str = Field(..., description="반박 ID")
    evidence_id: str = Field(..., description="대상 증거 ID")
    rebutter_user_id: str = Field(..., description="반박 작성자 user id")
    accepted: bool = Field(..., description="수용 여부")
    rebuttal: str | None = Field(None, description="반박 내용")
    created_at: datetime = Field(..., description="작성 시각")


class JudgmentSubmitRequest(BaseModel):
    """판단 등록 요청."""

    judgment_content: str | None = Field(None, description="판단 요지")
    fault_ratio_creator: int = Field(..., ge=0, le=100, description="원고 과실 비율 0~100")
    fault_ratio_counterparty: int = Field(
        ..., ge=0, le=100, description="피고 과실 비율 0~100"
    )


class CaseResultsResponse(BaseModel):
    """사건 판단(결과) 응답."""

    case_id: str = Field(..., description="사건 ID")
    judgment_content: str | None = Field(None, description="판단 요지")
    fault_ratio_creator: int | None = Field(None, description="원고 과실 비율 0~100")
    fault_ratio_counterparty: int | None = Field(None, description="피고 과실 비율 0~100")
    judged_at: datetime | None = Field(None, description="판단 시각")
    status: str = Field(..., description="진행 상태 (judged 등)")
