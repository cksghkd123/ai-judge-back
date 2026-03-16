"""
AI 판단용 프롬프트·응답 형식 설정.
/judge 폴더 안에서 프롬프트 요청 내용과 응답 형식을 수정할 수 있습니다.
"""

# ---------------------------------------------------------------------------
# 응답 형식: AI가 반드시 이 키로 JSON을 반환해야 함
# ---------------------------------------------------------------------------
RESPONSE_KEYS = (
    "judgment_content",  # 판단 요지 (str)
    "fault_ratio_claimant",  # 청구인 과실 비율 0~100 (int)
    "fault_ratio_respondent",  # 응답인 과실 비율 0~100 (int)
)

# ---------------------------------------------------------------------------
# 출력 지시: 모든 에이전트에 공통으로 붙는 JSON 형식 안내
# ---------------------------------------------------------------------------
OUTPUT_INSTRUCTION = """
응답은 반드시 JSON 한 덩어리만 출력하세요. 다른 설명은 붙이지 마세요.
키: judgment_content(판단 요지, 문자열), fault_ratio_claimant(청구인 과실 비율 0~100 정수), fault_ratio_respondent(응답인 과실 비율 0~100 정수).
fault_ratio_claimant + fault_ratio_respondent = 100 이어야 합니다."""


def get_system_prompt_for_agent(persona: str, style: str | None = None) -> str:
    """에이전트의 자아(persona) + 말투(style) + 공통 출력 지시를 합쳐 시스템 프롬프트 반환."""
    parts = [(persona or "").strip()]
    if (style or "").strip():
        parts.append(f"말투: {(style or '').strip()}")
    return "\n\n".join(parts) + OUTPUT_INSTRUCTION


# 레거시: 단일 시스템 프롬프트 (기본 에이전트와 동일)
SYSTEM_PROMPT = get_system_prompt_for_agent(
    "당신은 제시된 사건과 양측의 증거·반박을 바탕으로 공정히 판단하는 역할입니다."
)


def build_user_prompt(context: dict) -> str:
    """
    사건·증거(반박 포함) 정보로 사용자 프롬프트 문자열 생성.
    context: {
        "case": { "title", "description", "issue", "claimant_id", "respondent_id" },
        "claimant_evidences": [ { "id", "type", "content", "file_path", "rebuttals": [ {...} ] }, ... ],
        "respondent_evidences": [ ... ],
    }
    각 증거 항목에 그 증거에 대한 반박(rebuttals)이 묶여 있음.
    """
    case = context.get("case") or {}
    claimant_evidences = context.get("claimant_evidences") or []
    respondent_evidences = context.get("respondent_evidences") or []

    lines = [
        "## 사건",
        f"제목: {case.get('title', '')}",
        f"설명: {case.get('description', '')}",
        f"논점: {case.get('issue', '')}",
        "",
        "## 청구인(claimant) 측 증거 (각 항목 아래에 해당 증거에 대한 상대방 반박을 함께 적음)",
    ]
    for i, e in enumerate(claimant_evidences, 1):
        lines.append(
            f"  [Exhibit C{i}] type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}"
        )
        for r in e.get("rebuttals") or []:
            acc = "수용" if r.get("accepted") else "불수용"
            lines.append(f"    → 상대 반박: {acc}, rebuttal={r.get('rebuttal') or '(없음)'}")
    lines.append("")
    lines.append("## 응답인(respondent) 측 증거 (각 항목 아래에 해당 증거에 대한 상대방 반박을 함께 적음)")
    for i, e in enumerate(respondent_evidences, 1):
        lines.append(
            f"  [Exhibit R{i}] type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}"
        )
        for r in e.get("rebuttals") or []:
            acc = "수용" if r.get("accepted") else "불수용"
            lines.append(f"    → 상대 반박: {acc}, rebuttal={r.get('rebuttal') or '(없음)'}")
    lines.append("")
    lines.append(
        "위 사건에 대해 판단 요지(judgment_content)와 청구인·응답인 과실 비율(fault_ratio_claimant, fault_ratio_respondent, 합 100)을 JSON으로만 답하세요."
    )
    return "\n".join(lines)
