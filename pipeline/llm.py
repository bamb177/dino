"""Claude 호출 공통부: JSON 스키마로 구조화된 답을 받습니다."""
import json
import os

MODEL = "claude-opus-5-5"


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def ask_json(prompt: str, schema: dict, effort: str = "medium") -> dict:
    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude 가 이 요청을 거절했습니다. 주제를 바꿔 다시 시도하세요.")
    return json.loads(next(b.text for b in response.content if b.type == "text"))
