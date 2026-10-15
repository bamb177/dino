"""밈 대본 생성: ANTHROPIC_API_KEY 가 있으면 Claude 로, 없으면 예시 대본으로."""
import json
import random

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string"},
                    "mood": {"type": "string", "enum": ["normal", "happy", "sad", "shock"]},
                    "scene": {"type": "string"},
                },
                "required": ["caption", "mood", "scene"],
                "additionalProperties": False,
            },
        },
        "description": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "beats", "description", "hashtags"],
    "additionalProperties": False,
}

FALLBACK_SCRIPTS = [
    {
        "title": "월요일 아침",
        "beats": [
            {"caption": "일요일 밤 11시: 내일은 일찍 일어나야지", "mood": "happy", "scene": "침대에서 알람을 맞추며 뿌듯해하는 모습"},
            {"caption": "월요일 아침 8시 50분", "mood": "shock", "scene": "시계를 보고 화들짝 놀라는 모습"},
            {"caption": "오늘도 버텼다 룡…", "mood": "sad", "scene": "지하철 손잡이에 매달려 멍하니 서 있는 모습"},
        ],
        "description": "월요일은 왜 매주 오는 걸까요",
        "hashtags": ["#직장인", "#월요병", "#공룡", "#밈", "#shorts"],
    },
    {
        "title": "월급날",
        "beats": [
            {"caption": "월급 들어왔다!!", "mood": "happy", "scene": "폰 알림을 보고 환호하는 모습"},
            {"caption": "카드값, 월세, 보험료…", "mood": "shock", "scene": "쏟아지는 청구서에 둘러싸인 모습"},
            {"caption": "통장 스쳐 지나간 월급 룡…", "mood": "sad", "scene": "텅 빈 통장을 들여다보며 한숨 쉬는 모습"},
        ],
        "description": "월급은 로그인했다가 바로 로그아웃",
        "hashtags": ["#월급날", "#직장인공감", "#공룡", "#밈", "#shorts"],
    },
]


def generate_script(character: dict, topic: str | None = None, feedback: list[str] | None = None) -> dict:
    """topic 에는 매니저가 고른 트렌드 각도가, feedback 에는 직전 검수의 지적 사항이 들어옵니다."""
    from . import llm

    if not llm.available():
        return random.choice(FALLBACK_SCRIPTS)

    prompt = (
        "다음 캐릭터로 9~12초짜리 세로 숏폼 밈 대본을 써줘. "
        "3~4개의 짧은 자막 장면(beats)으로 구성하고, 첫 장면은 1초 안에 시선을 끄는 훅, "
        "마지막 장면은 반전이나 공감 포인트로 끝내. 자막 한 장면은 25자 이내. "
        "scene 에는 영상 생성 AI 에게 줄 그 장면의 시각 묘사를 한 문장으로 써. "
        "특정 크리에이터의 영상, 말투, 음악을 따라 하지 말고 캐릭터만의 오리지널 상황으로 만들어.\n\n"
        f"캐릭터 설정(JSON):\n{json.dumps(character, ensure_ascii=False)}\n\n"
        f"주제: {topic or '캐릭터 테마 중 하나를 골라 자유롭게'}"
    )
    if feedback:
        prompt += "\n\n직전 초안은 검수에서 반려되었어. 아래 지적을 반드시 고쳐서 다시 써줘:\n- " + "\n- ".join(feedback)
    return llm.ask_json(prompt, SCHEMA)
