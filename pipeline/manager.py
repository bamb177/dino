"""매니저 Claude: 트렌드에서 소재를 고르고, 대본을 검수해서 올릴지 말지 결정합니다."""
import json

from . import history, llm
from .script import generate_script

PICK_SCHEMA = {
    "type": "object",
    "properties": {
        "keyword": {"type": "string"},
        "angle": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["keyword", "angle", "reason"],
    "additionalProperties": False,
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["approved", "issues"],
    "additionalProperties": False,
}

REVIEW_RULES = """\
- 오리지널: 특정 크리에이터의 영상/말투/유행어 문장을 그대로 가져오지 않았다 (YouTube 반복·재사용 콘텐츠 정책)
- 안전: 실존 인물, 브랜드, 정치, 재난·사고·사망, 혐오, 선정성이 없다
- 광고 친화: 욕설과 자극적인 표현이 없다
- 저작권: 유행하는 음악/효과음/캐릭터를 요구하지 않는다
- 재미: 첫 장면이 훅이고 마지막 장면에 반전이나 공감 포인트가 있다
- 형식: 장면 3~4개, 자막 25자 이내, 총 9~12초 분량
- 중복: 최근 영상과 소재나 개그 구조가 겹치지 않는다
"""


def pick_topic(trends: list[dict], character: dict) -> str | None:
    """None 이면 캐릭터 테마로 자유 주제를 씁니다."""
    if not trends or not llm.available():
        return None
    prompt = (
        "너는 숏폼 밈 채널의 PD 야. 아래 '요즘 뜨는 키워드' 중에서, 이 캐릭터가 오리지널 상황극으로 "
        "풀 수 있는 소재 하나를 골라. 재난·사고·정치·실존 인물·논란 키워드는 피하고, 최근 영상과 겹치지 않게 해. "
        "적당한 게 없으면 keyword 를 '없음'으로 하고 캐릭터 테마에서 angle 을 제안해.\n\n"
        f"캐릭터:\n{json.dumps(character, ensure_ascii=False)}\n\n"
        f"요즘 뜨는 키워드:\n{json.dumps(trends, ensure_ascii=False)}\n\n"
        f"최근 영상 제목:\n{json.dumps(history.recent_titles(), ensure_ascii=False)}"
    )
    pick = llm.ask_json(prompt, PICK_SCHEMA)
    print(f"[manager] 소재: {pick['keyword']} / {pick['angle']} ({pick['reason']})")
    return f"트렌드 '{pick['keyword']}' 를 캐릭터 상황극으로: {pick['angle']}"


def review(script: dict, character: dict) -> dict:
    if not llm.available():
        return {"approved": True, "issues": []}
    prompt = (
        "너는 숏폼 채널의 엄격한 편집장이야. 아래 대본이 모든 기준을 통과하면 approved=true, "
        "하나라도 어기면 false 로 하고 issues 에 고칠 점을 구체적으로 적어.\n\n"
        f"기준:\n{REVIEW_RULES}\n"
        f"캐릭터:\n{json.dumps(character, ensure_ascii=False)}\n\n"
        f"대본:\n{json.dumps(script, ensure_ascii=False)}\n\n"
        f"최근 영상 제목:\n{json.dumps(history.recent_titles(), ensure_ascii=False)}"
    )
    return llm.ask_json(prompt, REVIEW_SCHEMA, effort="high")


def produce_script(trends: list[dict], character: dict, topic: str | None = None, max_tries: int = 3):
    """(script, approved, issues) 를 돌려줍니다. 승인 못 받으면 approved=False 로 올리지 않습니다."""
    topic = topic or pick_topic(trends, character)
    feedback: list[str] = []
    verdict = {"approved": False, "issues": ["대본 생성 실패"]}
    script = None
    for attempt in range(1, max_tries + 1):
        script = generate_script(character, topic, feedback or None)
        verdict = review(script, character)
        print(f"[manager] 시도 {attempt}: {'승인' if verdict['approved'] else '반려 - ' + '; '.join(verdict['issues'])}")
        if verdict["approved"]:
            break
        feedback = verdict["issues"]
    return script, verdict["approved"], verdict["issues"]
