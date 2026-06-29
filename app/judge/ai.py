"""
AI 판단 요청: status=judging 인 사건에 대해 데이터 수집 → 프롬프트 생성 → AI 호출 → 결과 반영.
비동기로 호출하며, 완료 시 status=completed 로 갱신합니다.
"""

from datetime import datetime, timezone

from anthropic import AsyncAnthropic

from app.clients.supabase import get_supabase
from app.config import settings
from app.judge.agents import get_agent
from app.judge.prompts import (
    build_user_prompt,
    get_system_prompt_for_agent,
)
from app.schemas.case import JudgmentResult

EVIDENCE_IMAGE_URL_EXPIRES_IN = 3600


def _signed_url_for_storage_path(path: str) -> str | None:
    """Supabase Storage file_path에 대한 signed URL 생성."""
    bucket = (settings.supabase_storage_bucket or "").strip()
    if not bucket:
        return None
    if not (path or "").strip():
        return None
    supabase = get_supabase()
    storage = supabase.storage.from_(bucket)
    res = storage.create_signed_url(path.strip(), EVIDENCE_IMAGE_URL_EXPIRES_IN)
    # storage3: {"signedURL", "signedUrl"} 또는 객체
    if isinstance(res, dict):
        return res.get("signedUrl") or res.get("signedURL") or res.get("signed_url")
    return (
        getattr(res, "signedUrl", None)
        or getattr(res, "signedURL", None)
        or getattr(res, "signed_url", None)
    )


def _build_image_parts(context: dict) -> list[dict]:
    """
    증거 전역번호 순서(청구인→응답인) 그대로 이미지 파트를 생성.
    - chat/photo + file_path가 있는 증거만 첨부
    - 각 이미지 앞에 어떤 증거 번호인지 텍스트로 라벨링
    """
    parts: list[dict] = []

    evidence_no = 1
    for evidences in (
        context.get("claimant_evidences") or [],
        context.get("respondent_evidences") or [],
    ):
        for e in evidences:
            if (e.get("type") or "").strip() not in ("chat", "photo"):
                evidence_no += 1
                continue
            path = (e.get("file_path") or "").strip()
            if not path:
                evidence_no += 1
                continue
            try:
                url = _signed_url_for_storage_path(path)
            except Exception:
                url = None
            if not url:
                evidence_no += 1
                continue
            parts.append({"type": "text", "text": f"[이미지 첨부] 증거 {evidence_no}"})
            parts.append({"type": "image", "source": {"type": "url", "url": url}})
            evidence_no += 1

    return parts


def _gather_context(case_id: str) -> dict:
    """사건·양측 증거·반박을 조회해 프롬프트용 context dict 반환."""

    supabase = get_supabase()
    case_res = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not case_res.data or len(case_res.data) == 0:
        raise ValueError(f"Case not found: {case_id}")
    case_row = case_res.data[0]
    claimant_id = case_row["claimant_id"]
    respondent_id = case_row.get("respondent_id")
    if not respondent_id:
        raise ValueError("Case has no respondent")

    ev_res = (
        supabase.table("case_evidence")
        .select("id, user_id, type, content, file_path")
        .eq("case_id", case_id)
        .order("created_at", desc=False)
        .execute()
    )
    evidences = ev_res.data or []
    evidence_ids = [e["id"] for e in evidences]

    rebuttals_raw = []
    if evidence_ids:
        reb_res = (
            supabase.table("case_evidence_rebuttal")
            .select("evidence_id, rebutter_user_id, accepted, rebuttal")
            .in_("evidence_id", evidence_ids)
            .execute()
        )
        rebuttals_raw = list(reb_res.data or [])

    # evidence_id 별로 반박 묶기
    rebuttals_by_evidence: dict = {}
    for r in rebuttals_raw:
        eid = r.get("evidence_id")
        if eid is not None:
            rebuttals_by_evidence.setdefault(str(eid), []).append({
                "rebutter_user_id": r.get("rebutter_user_id"),
                "accepted": r.get("accepted"),
                "rebuttal": r.get("rebuttal"),
            })

    def with_rebuttals(ev_list: list) -> list:
        out = []
        for e in ev_list:
            item = dict(e)
            item["rebuttals"] = rebuttals_by_evidence.get(str(e.get("id")), [])
            out.append(item)
        return out

    claimant_evidences = with_rebuttals(
        [e for e in evidences if str(e["user_id"]) == str(claimant_id)]
    )
    respondent_evidences = with_rebuttals(
        [e for e in evidences if str(e["user_id"]) == str(respondent_id)]
    )

    return {
        "case": {
            "title": case_row.get("title"),
            "description": case_row.get("description"),
            "issue": case_row.get("issue"),
            "claimant_id": claimant_id,
            "respondent_id": respondent_id,
            "judge_agent_id": case_row.get("judge_agent_id") or "default",
        },
        "claimant_evidences": claimant_evidences,
        "respondent_evidences": respondent_evidences,
    }


async def request_judgment(case_id: str) -> None:
    """
    비동기: 사건 판단 요청.
    - context 수집 → 프롬프트 생성 → AI API 호출(structured outputs) → cases 업데이트(status=completed).
    출력 형식은 JudgmentResult 스키마로 강제되므로 별도 파싱/검증이 필요 없다.
    """
    if not (settings.anthropic_api_key or "").strip():
        # API 키 없으면 판단 스킵, status 는 judging 유지
        return

    context = _gather_context(case_id)
    user_prompt = build_user_prompt(context)
    image_parts = _build_image_parts(context)
    agent_id = context.get("case", {}).get("judge_agent_id") or "default"
    agent = get_agent(agent_id)
    system_prompt = get_system_prompt_for_agent(
        agent.persona, agent.style, agent.judgment_structure
    )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key.strip())
    user_content: str | list[dict]
    if image_parts:
        user_content = [{"type": "text", "text": user_prompt}, *image_parts]
    else:
        user_content = user_prompt
    resp = await client.messages.parse(
        model=(settings.anthropic_model or "claude-opus-4-8"),
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_content},
        ],
        output_format=JudgmentResult,
    )
    result = resp.parsed_output
    if result is None:
        return

    judgment_content = result.judgment_content or ""
    fault_claimant = max(0, min(100, int(result.fault_ratio_claimant)))
    fault_respondent = max(0, min(100, int(result.fault_ratio_respondent)))

    supabase = get_supabase()
    supabase.table("cases").update(
        {
            "judgment_content": judgment_content,
            "fault_ratio_claimant": fault_claimant,
            "fault_ratio_respondent": fault_respondent,
            "judged_at": datetime.now(tz=timezone.utc).isoformat(),
            "status": "completed",
        }
    ).eq("id", case_id).execute()
