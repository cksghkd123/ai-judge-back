"""
AI 판단 요청: status=judging 인 사건에 대해 데이터 수집 → 프롬프트 생성 → AI 호출 → 결과 반영.
비동기로 호출하며, 완료 시 status=completed 로 갱신합니다.
"""

import json
import re
from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.clients.supabase import get_supabase
from app.config import settings
from app.judge.agents import get_agent
from app.judge.prompts import (
    RESPONSE_KEYS,
    build_user_prompt,
    get_system_prompt_for_agent,
)


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
    claimant_evidences = [e for e in evidences if str(e["user_id"]) == str(claimant_id)]
    respondent_evidences = [e for e in evidences if str(e["user_id"]) == str(respondent_id)]
    evidence_ids = [e["id"] for e in evidences]

    rebuttals = []
    if evidence_ids:
        reb_res = (
            supabase.table("case_evidence_rebuttal")
            .select("evidence_id, rebutter_user_id, accepted, rebuttal")
            .in_("evidence_id", evidence_ids)
            .execute()
        )
        rebuttals = list(reb_res.data or [])

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
        "rebuttals": rebuttals,
    }


def _parse_ai_response(text: str) -> dict:
    """응답 텍스트에서 JSON을 추출하고 RESPONSE_KEYS 검증."""
    
    text = (text or "").strip()
    # JSON 블록만 추출 (```json ... ``` 또는 그냥 {...})
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if match:
        text = match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]
    data = json.loads(text)
    for key in RESPONSE_KEYS:
        if key not in data:
            raise ValueError(f"AI response missing key: {key}")
    return data


async def request_judgment(case_id: str) -> None:
    """
    비동기: 사건 판단 요청.
    - context 수집 → 프롬프트 생성 → AI API 호출 → 응답 파싱 → cases 업데이트(status=completed).
    """
    if not (settings.openai_api_key or "").strip():
        # API 키 없으면 판단 스킵, status 는 judging 유지
        return

    context = _gather_context(case_id)
    user_prompt = build_user_prompt(context)
    agent_id = context.get("case", {}).get("judge_agent_id") or "default"
    agent = get_agent(agent_id)
    system_prompt = get_system_prompt_for_agent(agent.persona, agent.style)

    client = AsyncOpenAI(api_key=settings.openai_api_key.strip())
    resp = await client.chat.completions.create(
        model=(settings.openai_model or "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        return

    data = _parse_ai_response(content)
    judgment_content = data.get("judgment_content") or ""
    fault_claimant = data.get("fault_ratio_claimant", 0)
    fault_respondent = data.get("fault_ratio_respondent", 0)
    fault_claimant = max(0, min(100, int(fault_claimant)))
    fault_respondent = max(0, min(100, int(fault_respondent)))

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
