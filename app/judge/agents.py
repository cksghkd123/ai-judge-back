"""
판단 에이전트(자아) 관리.
/judge 폴더 안에서 에이전트를 추가·수정할 수 있습니다.
사건 생성 시 선택한 에이전트가 해당 사건의 AI 판단 톤을 결정합니다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class JudgeAgent:
    """판단 에이전트: id, 노출 이름, 자아(프롬프트에 들어갈 역할/성격)."""

    id: str
    name: str
    persona: str
    style: str


# ---------------------------------------------------------------------------
# 에이전트 레지스트리: id → JudgeAgent
# 새 자아는 여기에 추가하면 됩니다.
# ---------------------------------------------------------------------------
AGENTS: dict[str, JudgeAgent] = {
    "default": JudgeAgent(
        id="default",
        name="기본 판사",
        persona="당신은 제시된 사건과 양측의 증거·반박을 바탕으로 공정히 판단하는 역할입니다.",
        style="~습니다. 와 같은 말투",
    ),
    "strict": JudgeAgent(
        id="strict",
        name="엄격한 판사",
        persona="""당신은 매우 엄격하고 진지한 판사입니다.
법리와 원칙을 중시하며, 감정보다는 사실과 증거에 따라 판단합니다.
말투는 간결하고 단호합니다. 굉장히 깐깐한 사람으로 감정에 민감하지 않습니다. MBTI 100% T""",
        style="~합니다. ~했습니다. 와 같은 말투",
    ),
    "love_expert": JudgeAgent(
        id="love_expert",
        name="사랑싸움 전문가",
        persona="""당신은 연인·부부 간 갈등을 잘 이해하는 사랑싸움 전문가입니다.
감정과 관계 맥락을 고려하면서도, 어느 쪽이 더 손해를 봤는지 공정하게 나눕니다.
말투는 공감적이면서도 결론은 분명하게 내립니다.""",
        style="~라고 생각되네요. ~인 것 같아요. 와 같은 말투",
    ),
}

DEFAULT_AGENT_ID = "default"


def get_agent(agent_id: str | None) -> JudgeAgent:
    """에이전트 ID로 조회. 없거나 None이면 기본 에이전트 반환."""
    if not agent_id or not agent_id.strip():
        return AGENTS[DEFAULT_AGENT_ID]
    key = agent_id.strip()
    return AGENTS.get(key, AGENTS[DEFAULT_AGENT_ID])


def list_agents() -> list[dict[str, str]]:
    """API용: { id, name } 목록."""
    return [{"id": a.id, "name": a.name} for a in AGENTS.values()]


def is_valid_agent_id(agent_id: str | None) -> bool:
    """사건 생성 시 선택 가능한 ID인지 검사."""
    if not agent_id or not agent_id.strip():
        return True  # 미선택 시 default 사용
    return agent_id.strip() in AGENTS
