"""사건(case) API 요청/응답 스키마."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateCaseRequest(BaseModel):
    """사건 생성 요청."""

    title: str = Field(..., min_length=1, description="사건 제목")
    description: str = Field(..., min_length=1, description="사건 설명")
    issue: str = Field(..., min_length=1, description="논점")
    claimant_name: str = Field(..., min_length=1, description="청구인 이름")
    claimant_address: str | None = Field(None, description="청구인 주소")
    claimant_jobs: list[str] = Field(default_factory=list, description="청구인 직업")
    claimant_profile_image: str | None = Field(
        None, description="청구인(claimant) 프로필 이미지 URL"
    )
    judge_agent_id: str = Field(
        default="default",
        description="판단 에이전트 ID. 미입력 시 default.",
    )


class JudgeAgentResponse(BaseModel):
    """판사 에이전트."""

    id: str = Field(..., description="에이전트 ID")
    name: str = Field(..., description="표시 이름")
    judge_image: str | None = Field(None, description="판사 이미지 URL")


class CreateCaseResponse(BaseModel):
    """사건 생성 응답."""

    id: str = Field(..., description="사건 ID")
    title: str = Field(..., description="사건 제목")
    description: str = Field(..., description="사건 설명")
    issue: str = Field(..., description="논점")
    status: str = Field(..., description="진행 상태")
    claimant_id: str = Field(..., description="청구인(claimant) user id")
    claimant_name: str = Field(..., description="청구인(claimant) 이름")
    claimant_address: str | None = Field(None, description="청구인(claimant) 주소")
    claimant_jobs: list[str] = Field(..., description="청구인(claimant) 직업")
    claimant_profile_image: str | None = Field(
        None, description="청구인(claimant) 프로필 이미지 URL"
    )
    created_at: datetime = Field(..., description="생성 시각")
    invite_token: str = Field(..., description="초대 토큰")
    judge_agent_id: str = Field(..., description="선택된 판단 에이전트 ID")


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
    my_role: str = Field(..., description="claimant | respondent")


class CasePreviewResponse(BaseModel):
    """사건 미리보기 (초대 링크용)"""

    id: str = Field(..., description="사건 ID")
    title: str = Field(..., description="사건 제목")
    description: str = Field(..., description="사건 설명")
    issue: str = Field(..., description="논점")
    status: str = Field(..., description="진행 상태")
    created_at: datetime = Field(..., description="생성 시각")
    claimant_name: str = Field(..., description="청구인 이름")
    claimant_address: str | None = Field(None, description="청구인 주소")
    claimant_jobs: list[str] = Field(default_factory=list, description="청구인 직업")
    claimant_profile_image: str | None = Field(
        None, description="청구인 프로필 이미지 URL"
    )


class CaseDetailResponse(BaseModel):
    """사건 상세 응답."""

    id: str = Field(..., description="사건 ID")
    title: str = Field(..., description="사건 제목")
    description: str = Field(..., description="사건 설명")
    issue: str = Field(..., description="논점")
    status: str = Field(..., description="진행 상태")
    claimant_id: str = Field(..., description="청구인 user id")
    claimant_name: str = Field(..., description="청구인 이름")
    claimant_address: str | None = Field(None, description="청구인 주소")
    claimant_jobs: list[str] = Field(..., description="청구인 직업")
    claimant_profile_image: str | None = Field(
        None, description="청구인 프로필 이미지 URL"
    )
    respondent_id: str | None = Field(None, description="응답인 user id")
    my_role: str = Field(..., description="claimant | respondent")
    created_at: datetime = Field(..., description="생성 시각")
    invite_token: str = Field(..., description="초대 토큰")
    claimant_evidence_complete: bool = Field(
        False, description="청구인 쪽 증거 제출 완료 여부"
    )
    respondent_evidence_complete: bool = Field(
        False, description="응답인 쪽 증거 제출 완료 여부"
    )
    claimant_rebuttal_complete: bool = Field(
        False, description="청구인 쪽 반박 완료 여부"
    )
    respondent_rebuttal_complete: bool = Field(
        False, description="응답인 쪽 반박 완료 여부"
    )
    judge_agent_id: str = Field(
        "default", description="이 사건에 사용되는 판단 에이전트 ID"
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


class JudgmentResult(BaseModel):
    """
    AI 판단 결과 — 출력 형식의 단일 소스(single source of truth).

    Claude structured outputs(`messages.parse`)로 이 스키마를 강제한다.
    출력 형식을 바꾸려면 여기 한 곳만 수정하면 프롬프트·검증·파싱이 함께 따라온다.
    내용 규칙(markdown, 합 100, 증거 인용)은 각 필드 description 에 담아 모델에 전달한다.
    """

    judgment_content: str = Field(
        ...,
        description=(
            "판단 요지. Markdown으로 작성(## 제목, - 목록, 1. 번호). "
            "본문에서 [증거 n]을 최소 3개 이상 인용하고, 각 증거에 대한 반박도 함께 언급하며 "
            "논리적으로 서술. 문단 구분은 빈 줄로."
        ),
    )
    fault_ratio_claimant: int = Field(
        ...,
        ge=0,
        le=100,
        description="청구인(claimant) 과실 비율 0~100 정수. respondent와 합이 반드시 100.",
    )
    fault_ratio_respondent: int = Field(
        ...,
        ge=0,
        le=100,
        description="응답인(respondent) 과실 비율 0~100 정수. claimant와 합이 반드시 100.",
    )


class JudgmentSubmitRequest(BaseModel):
    """판단 등록 요청."""

    judgment_content: str | None = Field(None, description="판단 요지")
    fault_ratio_claimant: int = Field(
        ..., ge=0, le=100, description="청구인(claimant) 과실 비율 0~100"
    )
    fault_ratio_respondent: int = Field(
        ..., ge=0, le=100, description="응답인(respondent) 과실 비율 0~100"
    )


class CaseResultsResponse(BaseModel):
    """사건 판단(결과) 응답."""

    case_id: str = Field(..., description="사건 ID")
    judgment_content: str | None = Field(None, description="판단 요지")
    fault_ratio_claimant: int | None = Field(
        None, description="청구인(claimant) 과실 비율 0~100"
    )
    fault_ratio_respondent: int | None = Field(
        None, description="응답인(respondent) 과실 비율 0~100"
    )
    judged_at: datetime | None = Field(None, description="판단 시각")
    status: str = Field(..., description="진행 상태 (judged 등)")
