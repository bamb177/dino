"""이미 만든 영상 기록. 같은 소재를 반복하지 않도록 매니저가 참고합니다."""
import json
from datetime import date
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "history.json"


def load() -> list[dict]:
    return json.loads(PATH.read_text()) if PATH.exists() else []


def add(entry: dict) -> None:
    items = load()
    items.append({"date": date.today().isoformat(), **entry})
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n")


def recent_titles(n: int = 20) -> list[str]:
    return [i.get("title", "") for i in load()[-n:]]
