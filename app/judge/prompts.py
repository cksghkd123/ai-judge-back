"""
AI 판단용 프롬프트·응답 형식 설정.
/judge 폴더 안에서 프롬프트 요청 내용과 응답 형식을 수정할 수 있습니다.
"""

# ---------------------------------------------------------------------------
# 응답 형식: AI가 반드시 이 키로 JSON을 반환해야 함
# ---------------------------------------------------------------------------
RESPONSE_KEYS = (
    "judgment_content",       # 판단 요지 (str)
    "fault_ratio_creator",    # 원고 과실 비율 0~100 (int)
    "fault_ratio_counterparty",  # 피고 과실 비율 0~100 (int)
)

# ---------------------------------------------------------------------------
# 출력 지시: 모든 에이전트에 공통으로 붙는 JSON 형식 안내
# ---------------------------------------------------------------------------
OUTPUT_INSTRUCTION = """
응답은 반드시 JSON 한 덩어리만 출력하세요. 다른 설명은 붙이지 마세요.
키: judgment_content(판단 요지, 문자열), fault_ratio_creator(원고 과실 비율 0~100 정수), fault_ratio_counterparty(피고 과실 비율 0~100 정수).
fault_ratio_creator + fault_ratio_counterparty = 100 이어야 합니다."""


def get_system_prompt_for_agent(persona: str) -> str:
    """에이전트의 자아(persona) + 공통 출력 지시를 합쳐 시스템 프롬프트 반환."""
    return (persona or "").strip() + OUTPUT_INSTRUCTION


# 레거시: 단일 시스템 프롬프트 (기본 에이전트와 동일)
SYSTEM_PROMPT = get_system_prompt_for_agent(
    "당신은 제시된 사건과 양측의 증거·반박을 바탕으로 공정히 판단하는 역할입니다."
)


def build_user_prompt(context: dict) -> str:
    """
    사건·증거·반박 정보로 사용자 프롬프트 문자열 생성.
    context: {
        "case": { "title", "description", "issue", "created_by", "counterpart_id" },
        "creator_evidences": [ { "type", "content", "file_path" }, ... ],
        "counterparty_evidences": [ ... ],
        "rebuttals": [ { "evidence_id", "rebutter_user_id", "accepted", "rebuttal" }, ... ]
    }
    """
    case = context.get("case") or {}
    creator_evidences = context.get("creator_evidences") or []
    counterparty_evidences = context.get("counterparty_evidences") or []
    rebuttals = context.get("rebuttals") or []

    lines = [
        "## 사건",
        f"제목: {case.get('title', '')}",
        f"설명: {case.get('description', '')}",
        f"논점: {case.get('issue', '')}",
        "",
        "## 원고(생성자) 측 증거",
    ]
    for i, e in enumerate(creator_evidences, 1):
        lines.append(f"  {i}. type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}")
    lines.append("")
    lines.append("## 피고(상대방) 측 증거")
    for i, e in enumerate(counterparty_evidences, 1):
        lines.append(f"  {i}. type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}")
    lines.append("")
    lines.append("## 반박 (증거별 상대방 의견)")
    for r in rebuttals:
        lines.append(f"  evidence_id={r.get('evidence_id')}, accepted={r.get('accepted')}, rebuttal={r.get('rebuttal') or '(없음)'}")
    lines.append("")
    lines.append("위 사건에 대해 판단 요지(judgment_content)와 원고·피고 과실 비율(fault_ratio_creator, fault_ratio_counterparty, 합 100)을 JSON으로만 답하세요.")
    return "\n".join(lines)
