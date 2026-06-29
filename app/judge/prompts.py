"""
AI 판단용 프롬프트 구성.
출력 형식(스키마)은 app/schemas/case.py 의 JudgmentResult 가 단일 소스이며,
ai.py 에서 Claude structured outputs 로 강제한다. 여기서는 시스템/유저 프롬프트만 만든다.

에이전트의 자아(persona)·말투(style)·전개방식(judgment_structure)은 모두 DB(judge_agents)에서 오고,
이 모듈은 그 값을 조립만 한다. (과거의 이름-매칭 하드코딩 제거)
"""

# ---------------------------------------------------------------------------
# 출력 내용 가이드: 형식 구조는 JudgmentResult 스키마가 강제하므로,
# 여기서는 judgment_content 의 '내용/서식' 규칙만 가볍게 안내한다.
# ---------------------------------------------------------------------------
OUTPUT_GUIDANCE = """
판단 요지(judgment_content)는 Markdown으로 보기 좋게 작성하세요. (예: ## 제목, - 목록, 1. 번호)
문단 구분은 빈 줄로 합니다.
청구인·응답인 과실 비율은 두 값의 합이 반드시 100이 되어야 합니다.
""".strip()


def get_system_prompt_for_agent(
    persona: str,
    style: str | None = None,
    judgment_structure: str | None = None,
) -> str:
    """에이전트의 자아(persona) + 말투(style) + 전개방식(judgment_structure) + 출력 가이드를 합쳐 시스템 프롬프트 반환."""
    parts = [(persona or "").strip()]
    if (style or "").strip():
        parts.append(f"말투: {(style or '').strip()}")
    if (judgment_structure or "").strip():
        parts.append((judgment_structure or "").strip())
    return "\n\n".join(p for p in parts if p) + "\n\n" + OUTPUT_GUIDANCE


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
        "## 청구인(claimant) 측 증거 (각 증거 아래에 해당 증거에 대한 상대방 반박 포함)",
    ]

    evidence_no = 1
    for e in claimant_evidences:
        lines.append(
            f"  [증거 {evidence_no}] type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}"
        )
        for r in e.get("rebuttals") or []:
            acc = "수용" if r.get("accepted") else "불수용"
            lines.append(
                f"    → 상대 반박: {acc}, rebuttal={r.get('rebuttal') or '(없음)'}"
            )
        evidence_no += 1
    lines.append("")
    lines.append(
        "## 응답인(respondent) 측 증거 (각 증거 아래에 해당 증거에 대한 상대방 반박 포함)"
    )
    for e in respondent_evidences:
        lines.append(
            f"  [증거 {evidence_no}] type={e.get('type')}, content={e.get('content') or '(없음)'}, file_path={e.get('file_path') or '(없음)'}"
        )
        for r in e.get("rebuttals") or []:
            acc = "수용" if r.get("accepted") else "불수용"
            lines.append(
                f"    → 상대 반박: {acc}, rebuttal={r.get('rebuttal') or '(없음)'}"
            )
        evidence_no += 1
    lines.append("")
    lines.append(
        "판단문(judgment_content)에서 위 [증거 n]을 반드시 인용하세요. 최소 3개 이상 인용할 것. 증거를 예로 들면서 그 증거에 대한 반박도 함께 언급하며 논리적으로 판단하세요."
    )
    lines.append("")
    lines.append(
        "참고: chat/photo 증거는 이미지가 함께 첨부됩니다. '[이미지 첨부] 증거 n' 라벨이 붙은 이미지를 해당 [증거 n]과 연결해 판단하세요."
    )
    lines.append("")
    lines.append(
        "위 사건에 대해 판단 요지와 청구인·응답인 과실 비율(합 100)을 판단하세요."
    )
    return "\n".join(lines)
