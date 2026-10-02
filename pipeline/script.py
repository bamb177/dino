"""밈 대본 생성: ANTHROPIC_API_KEY 가 있으면 Claude 로, 없으면 예시 대본으로."""
import json
import os
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
                },
                "required": ["caption", "mood"],
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
        "title": "월요일 아침 디노",
        "beats": [
            {"caption": "일요일 밤 11시: 내일은 일찍 일어나야지", "mood": "happy"},
            {"caption": "월요일 아침 8시 50분", "mood": "shock"},
            {"caption": "오늘도 버텼다 디노…", "mood": "sad"},
        ],
        "description": "월요일은 왜 매주 오는 걸까요",
        "hashtags": ["#직장인", "#월요병", "#공룡", "#밈", "#shorts"],
    },
    {
        "title": "월급날 디노",
        "beats": [
            {"caption": "월급 들어왔다!!", "mood": "happy"},
            {"caption": "카드값, 월세, 보험료…", "mood": "shock"},
            {"caption": "통장 스쳐 지나간 월급 디노…", "mood": "sad"},
        ],
        "description": "월급은 로그인했다가 바로 로그아웃",
        "hashtags": ["#월급날", "#직장인공감", "#공룡", "#밈", "#shorts"],
    },
]


def generate_script(character: dict, topic: str | None = None) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return random.choice(FALLBACK_SCRIPTS)

    import anthropic

    client = anthropic.Anthropic()
    prompt = (
        "다음 캐릭터로 9~12초짜리 세로 숏폼 밈 대본을 써줘. "
        "3~4개의 짧은 자막 장면(beats)으로 구성하고, 마지막 장면에서 반전이나 공감 포인트로 끝내. "
        "자막 한 장면은 25자 이내. 매번 새로운 상황을 써서 반복적인 콘텐츠가 되지 않게 해.\n\n"
        f"캐릭터 설정(JSON):\n{json.dumps(character, ensure_ascii=False)}\n\n"
        f"주제: {topic or '캐릭터 테마 중 하나를 골라 자유롭게'}"
    )
    response = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("대본 생성 요청이 거절되었습니다. 주제를 바꿔 다시 시도하세요.")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
