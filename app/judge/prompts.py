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

# ---------------------------------------------------------------------------
# 에이전트별 판단문 전개 방식 (judgment_content 서술 구조)
# ---------------------------------------------------------------------------
JUDGMENT_STRUCTURE: dict[str, str] = {
    "공정한 판사": """
판단문 전개: 쟁점 정리 → 청구인 주장과 근거(Exhibit 인용) → 응답인 주장과 근거(Exhibit 인용) → 반박이 있는 증거는 반박 내용까지 함께 언급한 뒤 → 종합 판단과 과실 비율.
청구인·응답인 측 각각 최소 2개 이상의 Exhibit(C1, C2, R1, R2 등)을 반드시 인용하세요.""",
    "매우 엄격한 판사": """
판단문 전개: 1. 사실 인정 사항 2. 증거별 신빙성·증거능력 (각 단락 끝에 반드시 "근거: Exhibit C○, R○" 형식으로 인용) 3. 반박에 대한 채택·배척 사유(수용한 반박은 채택 사유, 불수용은 배척 사유를 한 문장으로 명시) 4. 결론 및 과실 비율.
번호를 붙여 1., 1-1., 2. 식으로 조목조목 서술하세요.""",
    "연애전문 판사": """
판단문 전개: 사건을 '상황 → 감정/기대 → 행동 → 결과' 흐름의 장면으로 재구성하고, 각 장면마다 해당하는 Exhibit을 최소 1개 이상 인용하세요. 공감 문장 1~2개와 판단 문장 1개를 세트로 반복한 뒤, 마지막에 결론과 과실 비율을 명확히 제시하세요. 스토리텔링하되 결론은 분명하게.""",
}


def get_system_prompt_for_agent(
    persona: str,
    style: str | None = None,
    agent_name: str | None = None,
) -> str:
    """에이전트의 자아(persona) + 말투(style) + 전개 방식(agent_name 매핑) + 공통 출력 지시를 합쳐 시스템 프롬프트 반환."""
    parts = [(persona or "").strip()]
    if (style or "").strip():
        parts.append(f"말투: {(style or '').strip()}")
    if agent_name and agent_name.strip() in JUDGMENT_STRUCTURE:
        parts.append(JUDGMENT_STRUCTURE[agent_name.strip()].strip())
    return "\n\n".join(parts) + "\n\n" + OUTPUT_INSTRUCTION


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
            lines.append(
                f"    → 상대 반박: {acc}, rebuttal={r.get('rebuttal') or '(없음)'}"
            )
    lines.append("")
    lines.append(
        "## 응답인(respondent) 측 증거 (각 항목 아래에 해당 증거에 대한 상대방 반박을 함께 적음)"
    )
    for i, e in enumerate(respondent_evidences, 1):
        lines.append(
            f"  [Exhibit R{i}] type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}"
        )
        for r in e.get("rebuttals") or []:
            acc = "수용" if r.get("accepted") else "불수용"
            lines.append(
                f"    → 상대 반박: {acc}, rebuttal={r.get('rebuttal') or '(없음)'}"
            )
    lines.append("")
    lines.append(
        "판단문(judgment_content)에서 위 Exhibit(C1, C2, R1, R2 등)을 반드시 인용하세요. 최소 3개 이상 인용할 것. 증거를 예로 들면서 그 증거에 대한 반박도 함께 언급하며 논리적으로 판단하세요."
    )
    lines.append("")
    lines.append(
        "위 사건에 대해 판단 요지(judgment_content)와 청구인·응답인 과실 비율(fault_ratio_claimant, fault_ratio_respondent, 합 100)을 JSON으로만 답하세요."
    )
    return "\n".join(lines)
