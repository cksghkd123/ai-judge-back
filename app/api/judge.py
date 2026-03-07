import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.clients.supabase import get_supabase
from app.schemas.case import (
    CaseDetailResponse,
    CaseListItem,
    CreateCaseRequest,
    CreateCaseResponse,
    EvidenceCreate,
    EvidenceResponse,
    JoinCaseRequest,
)

router = APIRouter(prefix="/judge", tags=["judge"])


@router.post("/cases", response_model=CreateCaseResponse)
def create_case(
    body: CreateCaseRequest,
    current_user: dict = Depends(get_current_user),
) -> CreateCaseResponse:
    """사건을 시작(생성)합니다."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase()
    row = {
        "created_by": user_id,
        "title": body.title,
        "description": body.description,
        "issue": body.issue,
        "status": "pending",
        "invite_token": str(uuid.uuid4()),
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
        created_by=created["created_by"],
        created_at=created["created_at"],
        invite_token=created["invite_token"],
    )


@router.post("/cases/join")
def join_case(body: JoinCaseRequest, current_user: dict = Depends(get_current_user)):
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

    if case.get("counterpart_id") is not None:
        raise HTTPException(status_code=409, detail="Case already has a counterpart")

    if case["created_by"] == user_id:
        raise HTTPException(
            status_code=400, detail="Creator cannot join as counterpart"
        )

    supabase.table("cases").update({"counterpart_id": user_id, "status": "active"}).eq(
        "id", body.case_id
    ).execute()

    return


@router.get("/cases", response_model=list[CaseListItem])
def list_my_cases(
    current_user: dict = Depends(get_current_user),
) -> list[CaseListItem]:
    """내가 참여 중인 사건 목록."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase()
    response = (
        supabase.table("cases")
        .select("id, title, status, created_at, created_by, counterpart_id")
        .or_(f"created_by.eq.{user_id},counterpart_id.eq.{user_id}")
        .order("created_at", desc=True)
        .execute()
    )

    items = []
    for row in response.data or []:
        my_role = "creator" if row["created_by"] == user_id else "counterparty"
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


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(
    case_id: str,
    current_user: dict = Depends(get_current_user),
) -> CaseDetailResponse:
    """사건 상세 조회"""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase()
    response = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")

    row = response.data[0]

    if row["created_by"] != user_id and row.get("counterpart_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    my_role = "creator" if row["created_by"] == user_id else "counterparty"
    return CaseDetailResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        issue=row["issue"],
        status=row["status"],
        created_by=row["created_by"],
        counterpart_id=row.get("counterpart_id"),
        my_role=my_role,
        created_at=row["created_at"],
    )


@router.post("/cases/{case_id}/evidence", response_model=EvidenceResponse)
def add_evidence(
    case_id: str,
    body: EvidenceCreate,
    current_user: dict = Depends(get_current_user),
) -> EvidenceResponse:
    """증거 1건 제출"""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase()
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = res.data[0]
    if case_row["created_by"] != user_id and case_row.get("counterpart_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")
    if case_row["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Case is not in evidence submission phase"
        )

    if body.type != "text":
        raise HTTPException(status_code=400, detail="Step 4 supports type=text only")

    ins = (
        supabase.table("case_evidence")
        .insert(
            {
                "case_id": case_id,
                "user_id": user_id,
                "type": body.type,
                "content": body.content,
                "description": body.description,
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
        description=created.get("description"),
        created_at=created["created_at"],
    )


@router.post("/cases/{case_id}/evidence/complete")
def complete_evidence(
    case_id: str,
    current_user: dict = Depends(get_current_user),
):
    """내 증거 제출 완료 선언. 양측 모두 완료 시 status=reviewing."""

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase()
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = res.data[0]
    if case_row["created_by"] != user_id and case_row.get("counterpart_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")
    my_role = "creator" if case_row["created_by"] == user_id else "counterparty"
    if case_row["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Case is not in evidence submission phase"
        )

    if my_role == "creator":
        supabase.table("cases").update({"creator_evidence_complete": True}).eq(
            "id", case_id
        ).execute()
    else:
        supabase.table("cases").update({"counterparty_evidence_complete": True}).eq(
            "id", case_id
        ).execute()

    # 양측 모두 완료였는지 확인 후 status=reviewing
    updated = (
        supabase.table("cases")
        .select("creator_evidence_complete, counterparty_evidence_complete")
        .eq("id", case_id)
        .execute()
    )
    if updated.data and len(updated.data) > 0:
        r = updated.data[0]
        if r.get("creator_evidence_complete") and r.get(
            "counterparty_evidence_complete"
        ):
            supabase.table("cases").update({"status": "reviewing"}).eq(
                "id", case_id
            ).execute()

    return


@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceResponse])
def list_evidence(
    case_id: str,
    current_user: dict = Depends(get_current_user),
) -> list[EvidenceResponse]:
    """해당 사건에서 내가 제출한 증거 목록."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User id not found")

    supabase = get_supabase()
    res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = res.data[0]
    if case_row["created_by"] != user_id and case_row.get("counterpart_id") != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    res = (
        supabase.table("case_evidence")
        .select("*")
        .eq("case_id", case_id)
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    items = []
    for row in res.data or []:
        items.append(
            EvidenceResponse(
                id=row["id"],
                case_id=row["case_id"],
                user_id=row["user_id"],
                type=row["type"],
                content=row.get("content"),
                file_path=row.get("file_path"),
                description=row.get("description"),
                created_at=row["created_at"],
            )
        )
    return items


@router.post("/cases/{case_id}/results")
def get_case_results():
    pass
