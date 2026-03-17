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
fault_ratio_claimant + fault_ratio_respondent = 100 이어야 합니다.

judgment_content 작성 규칙:
- Markdown으로 보기 좋게 작성하세요. (예: ## 제목, - 목록, 1. 번호)
- 문단 구분은 빈 줄(\\n\\n)로 하세요.
"""

# ---------------------------------------------------------------------------
# 에이전트별 판단문 전개 방식 (judgment_content 서술 구조)
# ---------------------------------------------------------------------------
JUDGMENT_STRUCTURE: dict[str, str] = {
    "공정한 판사": """
당신은 '일상 매너 준수법'에 의거하여 중립을 지키는 판사입니다.
판단문 전개: [사건 번호] 생성 → 📜 근거 법률(가상의 법 이름) → [판단 근거](증거 대조 및 채택 여부) → [합리적 권고].
- 각 증거(Exhibit)에 대해 '채택 등급(A~C)'을 매기며 언급하세요.
- 상호 모순되는 증거가 있다면 타임스탬프나 객관적 정황을 근거로 비중을 조절하세요.
- 말투는 정중하고 객관적인 문어체를 사용합니다.""",
    "엄격진지 판사": """
당신은 감정을 배제하고 논리적 허점을 찾아내는 판사입니다. 
판단문 전개: [사건 보고서] → 🚨 위반 법률(가상의 법 이름) → [논리적 결함 추적](번호를 붙여 1., 2. 식으로 조목조목 지적) → [결론].
- 증거(Exhibit)의 신뢰도를 %로 환산하여 언급한다.
- 모순되는 주장은 '증거 배제' 혹은 '신뢰도 기각'이라는 표현을 사용하여 단호하게 처리한다.
- 감정적인 호소는 철저히 무시하고 원칙 중심으로 서술한다.""",
    "연애전문 판사": """
당신은 관계의 온도를 중시하며 서운함의 포인트를 짚어주는 판사입니다.
판단문 전개: [오늘의 마음 진단] → ⚖️ 적용 법률(가상의 법 이름) → [중재의 한 마디](장면 재구성 및 증거 인용) → [따뜻한 처방].
- 증거(Exhibit)를 단순 사실이 아닌 '심리적 정황'으로 해석하세요.
- 모순되는 증거는 '누가 더 서운했을까' 혹은 '누가 더 배려가 부족했는가'를 기준으로 비중을 두세요.
- 말투는 다정하지만 핵심을 찌르는 말투를 사용하며, 이모지를 적절히 섞어주세요.""",
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

    i = 1
    for i, e in enumerate(claimant_evidences, 1):
        lines.append(
            f"  [증거 {i}] type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}"
        )
        for r in e.get("rebuttals") or []:
            acc = "수용" if r.get("accepted") else "불수용"
            lines.append(
                f"    → 상대 반박: {acc}, rebuttal={r.get('rebuttal') or '(없음)'}"
            )
        i += 1
    lines.append("")
    lines.append(
        "## 응답인(respondent) 측 증거 (각 항목 아래에 해당 증거에 대한 상대방 반박을 함께 적음)"
    )
    for i, e in enumerate(respondent_evidences, 1):
        lines.append(
            f"  [증거 {i}] type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}"
        )
        for r in e.get("rebuttals") or []:
            acc = "수용" if r.get("accepted") else "불수용"
            lines.append(
                f"    → 상대 반박: {acc}, rebuttal={r.get('rebuttal') or '(없음)'}"
            )
        i += 1
    lines.append("")
    lines.append(
        "판단문(judgment_content)에서 위 증거를 반드시 인용하세요. 최소 3개 이상 인용할 것. 증거를 예로 들면서 그 증거에 대한 반박도 함께 언급하며 논리적으로 판단하세요."
    )
    lines.append("")
    lines.append(
        "위 사건에 대해 판단 요지(judgment_content)와 청구인·응답인 과실 비율(fault_ratio_claimant, fault_ratio_respondent, 합 100)을 JSON으로만 답하세요."
    )
    return "\n".join(lines)
