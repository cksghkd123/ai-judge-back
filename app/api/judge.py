import uuid
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from app.api.auth import get_access_token, get_current_user
from app.clients.supabase import get_supabase, get_supabase_for_user
from app.config import settings
from app.judge.agents import is_valid_agent_id, list_agents
from app.judge.ai import request_judgment
from app.schemas.case import (
    CaseDetailResponse,
    CaseListItem,
    CasePreviewResponse,
    CaseResultsResponse,
    CreateCaseRequest,
    CreateCaseResponse,
    EvidenceResponse,
    JudgeAgentResponse,
    JoinCaseRequest,
    RebuttalRequest,
    RebuttalResponse,
)

router = APIRouter(prefix="/judge", tags=["judge"])


@router.get("/agents", response_model=list[JudgeAgentResponse])
def get_judge_agents() -> list[JudgeAgentResponse]:
    """판단 에이전트(자아) 목록. 사건 생성 시 선택용."""

    return [JudgeAgentResponse(**a) for a in list_agents()]


@router.post("/case", response_model=CreateCaseResponse)
def create_case(
    body: CreateCaseRequest,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> CreateCaseResponse:
    """사건을 시작(생성)합니다."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    agent_id = (body.judge_agent_id or "").strip() or "default"
    if not is_valid_agent_id(agent_id):
        agent_id = "default"

    supabase = get_supabase_for_user(access_token)
    row = {
        "claimant_id": user_id,
        "claimant_name": body.claimant_name,
        "claimant_address": body.claimant_address,
        "claimant_jobs": body.claimant_jobs,
        "claimant_profile_image": body.claimant_profile_image,
        "title": body.title,
        "description": body.description,
        "issue": body.issue,
        "status": "pending",
        "invite_token": str(uuid.uuid4()),
        "judge_agent_id": agent_id,
    }
    response = supabase.table("cases").insert(row).execute()

    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create case")

    created = response.data[0]
    return CreateCaseResponse(
        id=created["id"],
        title=created["title"],
        description=created["description"],
        issue=created["issue"],
        status=created["status"],
        claimant_id=created["claimant_id"],
        claimant_name=created["claimant_name"],
        claimant_address=created.get("claimant_address"),
        claimant_jobs=created["claimant_jobs"],
        claimant_profile_image=created.get("claimant_profile_image"),
        created_at=created["created_at"],
        invite_token=created["invite_token"],
        judge_agent_id=created["judge_agent_id"],
    )


@router.post("/case/join")
def join_case(
    body: JoinCaseRequest,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    """초대 토큰을 이용해 사건에 참여합니다."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase()
    response = supabase.table("cases").select("*").eq("id", body.case_id).execute()

    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")

    case = response.data[0]
    if case["invite_token"] != body.invite_token:
        raise HTTPException(status_code=401, detail="Invalid invite token")

    if case["status"] != "pending":
        raise HTTPException(status_code=400, detail="Case is not pending")

    if case.get("respondent_id") is not None:
        raise HTTPException(status_code=409, detail="Case already has a respondent")

    if case["claimant_id"] == user_id:
        raise HTTPException(
            status_code=400, detail="Claimant cannot join as respondent"
        )

    supabase.table("cases").update({"respondent_id": user_id, "status": "active"}).eq(
        "id", body.case_id
    ).execute()

    return


@router.get("/cases", response_model=list[CaseListItem])
def list_my_cases(
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> list[CaseListItem]:
    """내가 참여 중인 사건 목록."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    response = (
        supabase.table("cases")
        .select("id, title, status, created_at, claimant_id, respondent_id")
        .or_(f"claimant_id.eq.{user_id},respondent_id.eq.{user_id}")
        .order("created_at", desc=True)
        .execute()
    )

    items = []
    for row in response.data or []:
        my_role = "claimant" if row["claimant_id"] == user_id else "respondent"
        items.append(
            CaseListItem(
                id=row["id"],
                title=row["title"],
                status=row["status"],
                created_at=row["created_at"],
                my_role=my_role,
            )
        )

    return items


@router.get("/case/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> CaseDetailResponse:
    """사건 상세 조회"""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    response = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")

    row = response.data[0]

    if row["claimant_id"] != user_id and row.get("respondent_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    my_role = "claimant" if row["claimant_id"] == user_id else "respondent"
    return CaseDetailResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        issue=row["issue"],
        status=row["status"],
        claimant_id=row["claimant_id"],
        claimant_name=row["claimant_name"],
        claimant_address=row.get("claimant_address"),
        claimant_jobs=row.get("claimant_jobs") or [],
        claimant_profile_image=row.get("claimant_profile_image"),
        respondent_id=row.get("respondent_id"),
        my_role=my_role,
        created_at=row["created_at"],
        invite_token=row["invite_token"],
        claimant_evidence_complete=row.get("claimant_evidence_complete", False),
        respondent_evidence_complete=row.get("respondent_evidence_complete", False),
        claimant_rebuttal_complete=row.get("claimant_rebuttal_complete", False),
        respondent_rebuttal_complete=row.get("respondent_rebuttal_complete", False),
        judge_agent_id=row["judge_agent_id"],
    )


@router.get("/case/preview/{case_id}", response_model=CasePreviewResponse)
def get_case_preview(case_id: str) -> CasePreviewResponse:
    """사건 JOIN 때 확인용"""

    supabase = get_supabase()
    response = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")

    row = response.data[0]

    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail="Case is not pending")

    return CasePreviewResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        issue=row["issue"],
        status=row["status"],
        created_at=row["created_at"],
        claimant_name=row.get("claimant_name") or "",
        claimant_address=row.get("claimant_address"),
        claimant_jobs=row.get("claimant_jobs") or [],
        claimant_profile_image=row.get("claimant_profile_image"),
    )


@router.post("/case/{case_id}/evidence", response_model=EvidenceResponse)
async def add_evidence(
    case_id: str,
    type: str = Form(..., description="text | chat | photo"),
    content: str | None = Form(
        None, description="type=text일 때 본문(필수), type=chat|photo일 때 설명(선택)"
    ),
    file: UploadFile | None = File(
        None, description="type=chat|photo일 때 이미지 파일"
    ),
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> EvidenceResponse:
    """증거 1건 제출. text: Form만. chat/photo: file 필수(multipart)."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    if type not in ("text", "chat", "photo"):
        raise HTTPException(status_code=400, detail="type must be text, chat, or photo")

    supabase = get_supabase_for_user(access_token)
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = res.data[0]
    if case_row["claimant_id"] != user_id and case_row.get("respondent_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")
    if case_row["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Case is not in evidence submission phase"
        )

    content_val: str | None = (content or "").strip() or None
    file_path_val: str | None = None

    if type == "text":
        if not content_val:
            raise HTTPException(
                status_code=400, detail="content required for type=text"
            )
    else:
        # chat | photo: file 필수
        if not file or not file.filename:
            raise HTTPException(
                status_code=400, detail="file required for type=chat and type=photo"
            )
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="Only image files are allowed for chat/photo"
            )
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty file not allowed")
        # Storage 경로: {case_id}/{user_id}/{uuid}.{ext}
        # 원본 파일명은 공백/유니코드로 인해 Storage signed URL 생성 시 InvalidKey가 날 수 있어 버립니다.
        ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if not ext or len(ext) > 10:
            ext = "png" if (file.content_type or "").lower() == "image/png" else "jpg"
        safe_name = f"{uuid.uuid4()}.{ext}"
        storage_path = f"{case_id}/{user_id}/{safe_name}"
        bucket = settings.supabase_storage_bucket
        get_supabase().storage.from_(bucket).upload(
            storage_path,
            data,
            file_options={
                "content-type": file.content_type or "application/octet-stream"
            },
        )
        file_path_val = storage_path

    ins = (
        supabase.table("case_evidence")
        .insert(
            {
                "case_id": case_id,
                "user_id": user_id,
                "type": type,
                "content": content_val,
                "file_path": file_path_val,
            }
        )
        .execute()
    )
    if not ins.data or len(ins.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to add evidence")

    created = ins.data[0]
    return EvidenceResponse(
        id=created["id"],
        case_id=created["case_id"],
        user_id=created["user_id"],
        type=created["type"],
        content=created.get("content"),
        file_path=created.get("file_path"),
        created_at=created["created_at"],
    )


@router.post("/case/{case_id}/evidence/complete")
def complete_evidence(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    """내 증거 제출 완료 선언. 양측 모두 완료 시 status=rebutting"""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = res.data[0]
    if case_row["claimant_id"] != user_id and case_row.get("respondent_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")
    my_role = "claimant" if case_row["claimant_id"] == user_id else "respondent"
    if case_row["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Case is not in evidence submission phase"
        )

    if my_role == "claimant":
        supabase.table("cases").update({"claimant_evidence_complete": True}).eq(
            "id", case_id
        ).execute()
    else:
        supabase.table("cases").update({"respondent_evidence_complete": True}).eq(
            "id", case_id
        ).execute()

    # 양측 모두 완료였는지 확인 후 status=rebutting
    updated = (
        supabase.table("cases")
        .select("claimant_evidence_complete, respondent_evidence_complete")
        .eq("id", case_id)
        .execute()
    )
    if updated.data and len(updated.data) > 0:
        r = updated.data[0]
        if r.get("claimant_evidence_complete") and r.get(
            "respondent_evidence_complete"
        ):
            supabase.table("cases").update({"status": "rebutting"}).eq(
                "id", case_id
            ).execute()

    return


@router.get("/case/{case_id}/my-evidences", response_model=list[EvidenceResponse])
def list_my_evidence(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> list[EvidenceResponse]:
    """해당 사건에서 내가 제출한 증거 목록."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    response = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = response.data[0]
    if case_row["claimant_id"] != user_id and case_row["respondent_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    response = (
        supabase.table("case_evidence")
        .select("*")
        .eq("case_id", case_id)
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    items = []
    for row in response.data or []:
        items.append(
            EvidenceResponse(
                id=row["id"],
                case_id=row["case_id"],
                user_id=row["user_id"],
                type=row["type"],
                content=row.get("content"),
                file_path=row.get("file_path"),
                created_at=row["created_at"],
            )
        )
    return items


@router.get(
    "/case/{case_id}/counterpart-evidences", response_model=list[EvidenceResponse]
)
def list_counterpart_evidence(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> list[EvidenceResponse]:
    """해당 사건에서 상대가 제출한 증거 목록."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    response = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = response.data[0]
    if case_row["claimant_id"] != user_id and case_row.get("respondent_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    if case_row.get("respondent_id") is None:
        raise HTTPException(status_code=400, detail="Case has no respondent yet")

    # 상대방 user_id: 내가 claimant면 respondent_id, 내가 respondent면 claimant_id
    other_user_id = (
        case_row["claimant_id"]
        if user_id == case_row["respondent_id"]
        else case_row["respondent_id"]
    )

    response = (
        supabase.table("case_evidence")
        .select("*")
        .eq("case_id", case_id)
        .eq("user_id", other_user_id)
        .order("created_at", desc=False)
        .execute()
    )
    items = []
    for row in response.data or []:
        items.append(
            EvidenceResponse(
                id=row["id"],
                case_id=row["case_id"],
                user_id=row["user_id"],
                type=row["type"],
                content=row.get("content"),
                file_path=row.get("file_path"),
                created_at=row["created_at"],
            )
        )
    return items


@router.post(
    "/case/{case_id}/evidence/{evidence_id}/rebut",
    response_model=RebuttalResponse,
)
def rebut_evidence(
    case_id: str,
    evidence_id: str,
    body: RebuttalRequest,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> RebuttalResponse:
    """상대 증거에 대한 반박 제출/수정. status=rebutting일 때만 가능."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = res.data[0]
    if case_row["claimant_id"] != user_id and case_row.get("respondent_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")
    if case_row.get("status") != "rebutting":
        raise HTTPException(status_code=400, detail="Case is not in rebutting phase")

    other_user_id = (
        case_row["claimant_id"]
        if user_id == case_row["respondent_id"]
        else case_row["respondent_id"]
    )
    ev = (
        supabase.table("case_evidence")
        .select("id, user_id")
        .eq("id", evidence_id)
        .eq("case_id", case_id)
        .execute()
    )
    if not ev.data or len(ev.data) == 0:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if ev.data[0]["user_id"] != other_user_id:
        raise HTTPException(
            status_code=403, detail="Can only rebut counterpart evidence"
        )

    rebuttal_text = (body.rebuttal or "").strip() or None
    existing = (
        supabase.table("case_evidence_rebuttal")
        .select("id, accepted, rebuttal, created_at")
        .eq("evidence_id", evidence_id)
        .eq("rebutter_user_id", user_id)
        .execute()
    )
    if existing.data and len(existing.data) > 0:
        row = existing.data[0]
        supabase.table("case_evidence_rebuttal").update(
            {"accepted": body.accepted, "rebuttal": rebuttal_text}
        ).eq("id", row["id"]).execute()
        return RebuttalResponse(
            id=row["id"],
            evidence_id=evidence_id,
            rebutter_user_id=user_id,
            accepted=body.accepted,
            rebuttal=rebuttal_text,
            created_at=row["created_at"],
        )
    ins = (
        supabase.table("case_evidence_rebuttal")
        .insert(
            {
                "evidence_id": evidence_id,
                "rebutter_user_id": user_id,
                "accepted": body.accepted,
                "rebuttal": rebuttal_text,
            }
        )
        .execute()
    )
    if not ins.data or len(ins.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to add rebuttal")
    created = ins.data[0]
    return RebuttalResponse(
        id=created["id"],
        evidence_id=evidence_id,
        rebutter_user_id=user_id,
        accepted=created["accepted"],
        rebuttal=created.get("rebuttal"),
        created_at=created["created_at"],
    )


@router.get(
    "/case/{case_id}/rebuttals",
    response_model=list[RebuttalResponse],
)
def list_case_rebuttals(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> list[RebuttalResponse]:
    """해당 사건의 반박 목록(양측 포함)."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = res.data[0]
    if case_row["claimant_id"] != user_id and case_row.get("respondent_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    ev_res = (
        supabase.table("case_evidence")
        .select("id")
        .eq("case_id", case_id)
        .order("created_at", desc=False)
        .execute()
    )
    evidence_ids = [row["id"] for row in (ev_res.data or [])]
    if not evidence_ids:
        return []

    reb_res = (
        supabase.table("case_evidence_rebuttal")
        .select("id, evidence_id, rebutter_user_id, accepted, rebuttal, created_at")
        .in_("evidence_id", evidence_ids)
        .order("created_at", desc=False)
        .execute()
    )
    out = []
    for row in reb_res.data or []:
        out.append(
            RebuttalResponse(
                id=row["id"],
                evidence_id=row["evidence_id"],
                rebutter_user_id=row["rebutter_user_id"],
                accepted=row["accepted"],
                rebuttal=row.get("rebuttal"),
                created_at=row["created_at"],
            )
        )
    return out


@router.post("/case/{case_id}/rebuttal/complete")
def complete_rebuttal(
    case_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
):
    """내 반박 완료 선언. 양측 모두 완료 시 status=judging, 이후 AI 판단 비동기 요청."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = res.data[0]
    if case_row["claimant_id"] != user_id and case_row.get("respondent_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")
    if case_row.get("status") != "rebutting":
        raise HTTPException(status_code=400, detail="Case is not in rebutting phase")

    my_role = "claimant" if case_row["claimant_id"] == user_id else "respondent"
    if my_role == "claimant":
        supabase.table("cases").update({"claimant_rebuttal_complete": True}).eq(
            "id", case_id
        ).execute()
    else:
        supabase.table("cases").update({"respondent_rebuttal_complete": True}).eq(
            "id", case_id
        ).execute()

    updated = (
        supabase.table("cases")
        .select("claimant_rebuttal_complete, respondent_rebuttal_complete")
        .eq("id", case_id)
        .execute()
    )
    if updated.data and len(updated.data) > 0:
        r = updated.data[0]
        if r.get("claimant_rebuttal_complete") and r.get(
            "respondent_rebuttal_complete"
        ):
            supabase.table("cases").update({"status": "judging"}).eq(
                "id", case_id
            ).execute()
            background_tasks.add_task(request_judgment, case_id)

    return


@router.get(
    "/case/{case_id}/results",
    response_model=CaseResultsResponse,
)
def get_case_results(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> CaseResultsResponse:
    """사건 판단(결과) 조회."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase_for_user(access_token)
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    row = res.data[0]
    if row["claimant_id"] != user_id and row.get("respondent_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    return CaseResultsResponse(
        case_id=row["id"],
        judgment_content=row.get("judgment_content"),
        fault_ratio_claimant=row.get("fault_ratio_claimant"),
        fault_ratio_respondent=row.get("fault_ratio_respondent"),
        judged_at=row.get("judged_at"),
        status=row["status"],
    )
