"""
판단 에이전트(자아) 관리.
default만 하드코딩, 나머지는 DB(judge_agents)에서 조회.
"""

from dataclasses import dataclass

from app.clients.supabase import get_supabase


@dataclass
class JudgeAgent:
    """판단 에이전트: id, 노출 이름, 자아(프롬프트용), 이미지 URL, 말투(style)."""

    id: str
    name: str
    persona: str
    judge_image: str | None = None
    style: str | None = None


# ---------------------------------------------------------------------------
# default만 하드코딩. 나머지는 judge_agents 테이블에서 조회.
# ---------------------------------------------------------------------------
DEFAULT_AGENT_ID = "default"
DEFAULT_AGENT = JudgeAgent(
    id=DEFAULT_AGENT_ID,
    name="기본 판사",
    persona="당신은 제시된 사건과 양측의 증거·반박을 바탕으로 공정히 판단하는 역할입니다.",
    judge_image=None,
    style="~습니다. 와 같은 말투를 사용하세요.",
)


def get_agent(agent_id: str | None) -> JudgeAgent:
    """에이전트 ID로 조회. default 또는 없으면 하드코딩 기본값, 그 외는 DB에서 조회."""
    if not agent_id or not (key := agent_id.strip()):
        return DEFAULT_AGENT
    if key == DEFAULT_AGENT_ID:
        return DEFAULT_AGENT
    supabase = get_supabase()
    res = (
        supabase.table("judge_agents")
        .select("id, name, persona, judge_image, style")
        .eq("id", key)
        .execute()
    )
    if not res.data or len(res.data) == 0:
        return DEFAULT_AGENT
    row = res.data[0]
    return JudgeAgent(
        id=str(row["id"]),
        name=row["name"],
        persona=row["persona"],
        judge_image=row.get("judge_image"),
        style=row.get("style"),
    )


def list_agents() -> list[dict[str, str | None]]:
    """API용: default + DB 에이전트 목록. 각 항목 id, name, judge_image, style."""
    out = []
    supabase = get_supabase()
    res = (
        supabase.table("judge_agents")
        .select("id, name, judge_image")
        .order("created_at", desc=False)
        .execute()
    )
    for row in res.data or []:
        out.append(
            {
                "id": str(row["id"]),
                "name": row["name"],
                "judge_image": row.get("judge_image"),
            }
        )
    return out


def is_valid_agent_id(agent_id: str | None) -> bool:
    """사건 생성 시 선택 가능한 ID인지 검사. default 또는 judge_agents에 존재."""
    if not agent_id or not (key := agent_id.strip()):
        return True
    if key == DEFAULT_AGENT_ID:
        return True
    supabase = get_supabase()
    res = supabase.table("judge_agents").select("id").eq("id", key).limit(1).execute()
    return bool(res.data and len(res.data) > 0)
