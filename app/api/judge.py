import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.clients.supabase import get_supabase
from app.schemas.case import (
    CaseDetailResponse,
    CaseListItem,
    CreateCaseRequest,
    CreateCaseResponse,
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


@router.post("/cases/{case_id}/statements")
def submit_statement():
    pass


@router.post("/cases/{case_id}/results")
def get_case_results():
    pass
