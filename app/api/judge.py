import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.clients.supabase import get_supabase
from app.schemas.case import CreateCaseRequest, CreateCaseResponse

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


@router.post("/cases/{case_id}/statements")
def submit_statement():
    pass


@router.get("/cases/{case_id}/status")
def get_case_status():
    pass


@router.post("/cases/{case_id}/results")
def get_case_results():
    pass
