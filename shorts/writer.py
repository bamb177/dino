"""트렌드 수집 + AI 대본 작성.

트렌드는 '주제 아이디어'로만 쓰고, 남의 영상·밈 이미지·노래는 절대 가져오지 않습니다.
반복 콘텐츠로 보이지 않도록 형식·캐릭터·배경·전개를 매번 바꿉니다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import urllib.request
from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel, Field

from .characters import CAST, EMOTIONS
from .render import BACKGROUNDS

EFFECTS = ["none", "hearts", "sparkles", "rain", "snow", "sweat", "zzz", "question", "exclaim", "confetti", "music"]

FORMATS = {
    "skit": "두 캐릭터의 짧은 상황극. 반전이 있는 웃긴 결말.",
    "relatable": "'~할 때 특징' 같은 공감 시리즈. 한 캐릭터가 겪고 다른 캐릭터가 맞장구.",
    "quiz": "시청자에게 퀴즈나 밸런스 게임을 내고, 마지막에 댓글로 답하게 유도.",
    "diary": "한 캐릭터의 하루 일기 독백. 소소하고 따뜻한 마무리.",
    "fact": "'알고 있었어?' 귀여운 동물/자연 상식 하나를 캐릭터가 재밌게 설명. 사실만 말할 것.",
    "challenge": "캐릭터가 오늘의 소소한 도전(예: 일찍 일어나기)을 하는데 엉뚱하게 실패/성공.",
}

STATE = Path(__file__).resolve().parent.parent / "state" / "history.json"


class Scene(BaseModel):
    speaker: str = Field(description="말하는 캐릭터 key")
    line: str = Field(description="대사. 한국어 35자 이내, 자연스러운 구어체")
    emotion: str = Field(description="말하는 캐릭터 표정: " + ", ".join(EMOTIONS))
    listener_emotion: str = Field(description="듣는 캐릭터 표정")
    effect: str = Field(description="효과: " + ", ".join(EFFECTS))


class Script(BaseModel):
    title: str = Field(description="유튜브 제목. 30자 이내, 끝에 #shorts")
    hook: str = Field(description="화면 상단 고정 문구. 14자 이내, 궁금증 유발")
    description: str = Field(description="영상 설명 2~3줄 + 해시태그 3~5개")
    tags: List[str]
    scenes: List[Scene] = Field(description="6~9개 장면")


# ---------------------------------------------------------------- 트렌드

def trends(limit: int = 15) -> list[str]:
    out = []
    try:
        req = urllib.request.Request("https://trends.google.com/trending/rss?geo=KR", headers={"User-Agent": "Mozilla/5.0"})
        xml = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        out = re.findall(r"<item>\s*<title>(.*?)</title>", xml)[:limit]
    except Exception as e:
        print(f"[trends] 가져오기 실패(괜찮음, 계절 주제로 진행): {e.__class__.__name__}")
    return out


def season(today: dt.date) -> str:
    m = today.month
    base = {12: "겨울, 연말, 크리스마스", 1: "새해, 한겨울", 2: "겨울 끝자락, 발렌타인", 3: "봄, 새 학기",
            4: "벚꽃, 봄나들이", 5: "가정의 달, 소풍", 6: "초여름, 장마 준비", 7: "여름, 장마, 휴가",
            8: "한여름, 바다", 9: "가을, 추석 무렵", 10: "가을, 단풍, 할로윈", 11: "늦가을, 수능, 첫눈 기다림"}[m]
    wd = "주말" if today.weekday() >= 5 else ["월요일", "화요일", "수요일", "목요일", "금요일"][today.weekday()]
    return f"{base}, 오늘은 {wd}"


# ---------------------------------------------------------------- 다양성

def load_history() -> list[dict]:
    try:
        return json.loads(STATE.read_text("utf-8"))
    except Exception:
        return []


def save_history(entry: dict):
    h = load_history()
    h.append(entry)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(h[-120:], ensure_ascii=False, indent=1), "utf-8")


def plan(rnd: random.Random, history: list[dict]) -> dict:
    recent = history[-4:]
    fmts = [f for f in FORMATS if f not in [h.get("format") for h in recent[-3:]]] or list(FORMATS)
    fmt = rnd.choice(fmts)
    keys = list(CAST)
    solo = fmt in ("diary", "fact") and rnd.random() < .6
    if solo:
        used = [c for h in recent for c in h.get("cast", [])]
        cast = [min(keys, key=lambda k: (used.count(k), rnd.random()))]
    else:
        last = tuple(sorted(recent[-1]["cast"])) if recent else ()
        pairs = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:] if tuple(sorted((a, b))) != last]
        cast = list(rnd.choice(pairs))
        rnd.shuffle(cast)
    bgs = [b for b in BACKGROUNDS if b not in [h.get("background") for h in recent[-2:]]]
    return {"format": fmt, "cast": cast, "background": rnd.choice(bgs)}


# ---------------------------------------------------------------- 작성

def _clean(script: dict, p: dict) -> dict:
    cast = p["cast"]
    for sc in script["scenes"]:
        if sc["speaker"] not in cast:
            sc["speaker"] = cast[0]
        if sc["emotion"] not in EMOTIONS:
            sc["emotion"] = "happy"
        if sc.get("listener_emotion") not in EMOTIONS:
            sc["listener_emotion"] = "neutral"
        if sc["effect"] not in EFFECTS:
            sc["effect"] = "none"
        sc["background"] = p["background"]
    if "#shorts" not in script["title"].lower():
        script["title"] = script["title"][:90] + " #shorts"
    script.update(p)
    return script


def write_ai(p: dict, today: dt.date, trend_list: list[str], history: list[dict]) -> dict:
    import anthropic

    cast_desc = "\n".join(f"- key={k}, 이름={CAST[k].name}: {CAST[k].personality}" for k in p["cast"])
    recent_titles = "\n".join(f"- {h['title']}" for h in history[-15:]) or "(없음)"
    prompt = f"""귀여운 오리지널 캐릭터 유튜브 쇼츠 채널의 대본 작가로서 오늘 영상 1편의 대본을 써 주세요.

[등장 캐릭터] (이 캐릭터만 사용, speaker에는 key를 씀)
{cast_desc}

[형식] {p['format']}: {FORMATS[p['format']]}
[배경] {p['background']}
[날짜/계절] {today.isoformat()} / {season(today)}
[오늘 한국 검색 트렌드 (참고용 아이디어)]
{chr(10).join('- ' + t for t in trend_list) or '(없음)'}

[최근 올린 영상 제목: 겹치지 않게]
{recent_titles}

규칙:
- 트렌드는 누구나 공감할 일상 주제(날씨, 계절, 음식, 시험, 연휴 등)일 때만 가볍게 반영. 실존 인물, 연예인, 브랜드, 정치, 사건사고, 다른 작품의 캐릭터·대사·밈 문구는 절대 쓰지 말 것.
- 전 연령이 볼 수 있는 따뜻하고 웃긴 내용. 첫 장면 3초 안에 궁금증을 만들고 마지막 장면은 반전이나 시청자에게 던지는 질문으로 끝낼 것.
- 장면 6~9개, 각 대사 35자 이내. 전체 25~40초 분량.
- 캐릭터 성격이 대사에 드러나야 함. 표정과 효과는 대사 감정에 맞게 다양하게.
"""
    client = anthropic.Anthropic()
    resp = client.beta.messages.parse(
        model=os.environ.get("SCRIPT_MODEL", "claude-opus-5-5"),
        max_tokens=8000,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
        output_format=Script,
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError(f"대본 생성 실패: stop_reason={resp.stop_reason}")
    return _clean(resp.parsed_output.model_dump(), p)


def write_offline(p: dict, rnd: random.Random) -> dict:
    """API 키 없이 테스트할 때 쓰는 샘플 대본."""
    a = p["cast"][0]
    b = p["cast"][-1]
    na, nb = CAST[a].name, CAST[b].name
    scenes = [
        dict(speaker=a, line=f"{nb}야! 오늘 첫눈 온대!", emotion="surprised", listener_emotion="sleepy", effect="exclaim"),
        dict(speaker=b, line="음냐… 눈은 내일 볼래…", emotion="sleepy", listener_emotion="sad", effect="zzz"),
        dict(speaker=a, line="안 돼! 첫눈 오면 소원 빌어야 해!", emotion="angry", listener_emotion="surprised", effect="none"),
        dict(speaker=b, line="소원? 그럼 나는 붕어빵 백 개!", emotion="love", listener_emotion="happy", effect="hearts"),
        dict(speaker=a, line="좋아, 나는 키 크게 해주세요!", emotion="happy", listener_emotion="happy", effect="sparkles"),
        dict(speaker=b, line="근데… 창밖 봐봐. 비 오는데?", emotion="surprised", listener_emotion="sad", effect="rain"),
        dict(speaker=a, line="…그럼 붕어빵이라도 먹으러 가자!", emotion="happy", listener_emotion="love", effect="confetti"),
        dict(speaker=b, line="너희는 첫눈에 무슨 소원 빌 거야?", emotion="smug", listener_emotion="happy", effect="question"),
    ]
    if len(p["cast"]) == 1:
        for s in scenes:
            s["speaker"] = a
    script = dict(
        title=f"{na}의 첫눈 소원 대작전 #shorts",
        hook="첫눈 오면 빌 소원은?",
        description=f"{na}와 {nb}의 첫눈 기다리기 ☃️\n여러분의 첫눈 소원은 뭔가요?\n#쇼츠 #귀여운캐릭터 #첫눈",
        tags=["귀여운캐릭터", "애니메이션", "쇼츠", na, nb],
        scenes=scenes,
    )
    return _clean(script, p)


def write(seed: int, today: dt.date | None = None, offline: bool = False) -> dict:
    today = today or dt.date.today()
    rnd = random.Random(seed)
    history = load_history()
    p = plan(rnd, history)
    if offline or not os.environ.get("ANTHROPIC_API_KEY"):
        print("[writer] ANTHROPIC_API_KEY 없음 → 샘플 대본 사용")
        if len(p["cast"]) == 1:  # 샘플 대본은 2인용
            p["cast"].append(next(k for k in CAST if k != p["cast"][0]))
        return write_offline(p, rnd)
    return write_ai(p, today, trends(), history)
