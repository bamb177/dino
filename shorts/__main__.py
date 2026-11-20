"""사용법
  python -m shorts make [--out out] [--offline] [--seed N]
      → out/<id>.mp4, out/<id>.json, out/issue.md 생성
  python -m shorts upload --video out/<id>.mp4 --meta out/<id>.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from . import audio, render, writer
from .characters import CAST

KST = ZoneInfo("Asia/Seoul")


def make(out: Path, offline: bool, seed: int | None):
    now = dt.datetime.now(KST)
    seed = seed if seed is not None else int(time.time())
    vid = now.strftime("%Y%m%d-%H%M")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    script = writer.write(seed, now.date(), offline=offline)
    print(f"[1/3] 대본: {script['title']} ({script['format']}, {script['cast']}, {script['background']})")
    mix, scenes = audio.build(script, out / f"work-{vid}", render.FPS, seed)
    print(f"[2/3] 음성/음악 완료 ({scenes[-1]['start'] + scenes[-1]['dur']:.1f}초)")
    mp4 = out / f"{vid}.mp4"
    dur = render.render(script, scenes, mix, mp4, seed=seed % 1000)
    print(f"[3/3] 영상 완료: {mp4} ({dur:.1f}초, {time.time() - t0:.0f}초 걸림)")

    meta = {k: script[k] for k in ("title", "hook", "description", "tags", "format", "cast", "background")}
    meta.update(id=vid, seed=seed, duration=round(dur, 1), created=now.isoformat())
    (out / f"{vid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    lines = "\n".join(f"{i + 1}. **{CAST[s['speaker']].name}** ({s['emotion']}): {s['line']}" for i, s in enumerate(script["scenes"]))
    (out / "issue.md").write_text(f"""<!-- short-id: {vid} -->
## {meta['title']}

- 길이: {meta['duration']}초 · 형식: `{meta['format']}` · 캐릭터: {', '.join(CAST[c].name for c in meta['cast'])}
- 영상 보기: 아래 **Release** 링크에서 `{vid}.mp4` 를 눌러 재생

### 대본
{lines}

### 설명란
```
{meta['description']}
```

---
**검수 방법** (1분)
- 괜찮으면 오른쪽 Labels 에서 **`approved`** 추가 → 자동으로 유튜브에 예약 업로드돼요.
- 별로면 **`rejected`** 추가 → 영상이 삭제되고 이슈가 닫혀요.
""", "utf-8")
    if not offline:
        writer.save_history({"id": vid, "title": meta["title"], "format": meta["format"],
                             "cast": meta["cast"], "background": meta["background"]})
    print(f"VIDEO_ID={vid}")
    return vid


def main():
    ap = argparse.ArgumentParser(prog="shorts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--out", default="out")
    m.add_argument("--offline", action="store_true", help="API 없이 샘플 대본으로 테스트")
    m.add_argument("--seed", type=int)
    u = sub.add_parser("upload")
    u.add_argument("--video", required=True)
    u.add_argument("--meta", required=True)
    a = ap.parse_args()
    if a.cmd == "make":
        make(Path(a.out), a.offline, a.seed)
    else:
        from .youtube import upload
        upload(a.video, json.loads(Path(a.meta).read_text("utf-8")))


if __name__ == "__main__":
    main()
