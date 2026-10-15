"""영상 만들기. provider 를 고릅니다.

- local: 무료. Pillow 로 그린 캐릭터 + 자막 (render.py)
- grok:  xAI Grok Imagine. AI 가 만든 10초 영상 위에 한글 자막을 ffmpeg 로 입힙니다. XAI_API_KEY 필요, 유료.
"""
import os
import subprocess
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from .render import H, W, load_font, render_video, wrap_text

XAI_API = "https://api.x.ai/v1"
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-imagine-video-1.5")  # 더 싼 모델: grok-imagine-video-1.5-lite
GROK_RESOLUTION = os.environ.get("GROK_RESOLUTION", "720p")
GROK_SECONDS = 10


def make_video(script: dict, character: dict, out_path: Path, provider: str, char_png: Path | None = None) -> Path:
    if provider == "grok":
        return _grok(script, character, out_path)
    return render_video(script, character, out_path, char_png)


def _grok_prompt(script: dict, character: dict) -> str:
    scenes = " ".join(f"({i + 1}) {b['scene']}." for i, b in enumerate(script["beats"]))
    return (
        f"세로 숏폼 코미디 영상, 약 {GROK_SECONDS}초. 주인공: {character['species']}. "
        f"성격: {', '.join(character['personality'])}. 장면 순서: {scenes} "
        "귀여운 3D 애니메이션 스타일, 밝은 색감, 카메라는 고정, 화면에 글자나 자막은 넣지 마. "
        "실존 인물, 브랜드 로고, 배경 음악은 넣지 마."
    )


def _grok(script: dict, character: dict, out_path: Path) -> Path:
    """xAI Grok Imagine 영상 API (https://docs.x.ai). XAI_API_KEY 필요, 유료(API 크레딧)."""
    headers = {"Authorization": f"Bearer {os.environ['XAI_API_KEY']}", "Content-Type": "application/json"}
    r = requests.post(
        f"{XAI_API}/videos/generations",
        headers=headers,
        json={
            "model": GROK_MODEL,
            "prompt": _grok_prompt(script, character),
            "duration": GROK_SECONDS,
            "aspect_ratio": "9:16",
            "resolution": GROK_RESOLUTION,
        },
        timeout=60,
    )
    r.raise_for_status()
    request_id = r.json()["request_id"]

    for _ in range(120):  # 최대 약 10분
        time.sleep(5)
        status = requests.get(f"{XAI_API}/videos/{request_id}", headers=headers, timeout=60)
        status.raise_for_status()
        data = status.json()
        if data.get("status") == "done":
            break
        if data.get("status") in ("failed", "expired"):
            raise RuntimeError(f"Grok 영상 생성 실패: {data}")
    else:
        raise TimeoutError("Grok 영상 생성 대기 시간 초과")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw = out_path.with_name("grok_raw.mp4")
    video = requests.get(data["video"]["url"], timeout=120)
    video.raise_for_status()
    raw.write_bytes(video.content)
    return burn_captions(raw, script, out_path, GROK_SECONDS)


def burn_captions(clip: Path, script: dict, out_path: Path, seconds: float) -> Path:
    """클립을 1080x1920 으로 맞추고 장면별 자막과 'AI 생성 콘텐츠' 표기를 입힙니다."""
    beats = script["beats"]
    per = seconds / len(beats)
    font, label_font = load_font(78), load_font(34)
    overlays = []
    for i, beat in enumerate(beats):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        lines = wrap_text(d, beat["caption"], font, W - 160)
        box_h = 110 * len(lines) + 60
        d.rounded_rectangle([60, 330, W - 60, 330 + box_h], radius=40, fill="white", outline="#222", width=6)
        for j, line in enumerate(lines):
            d.text((W / 2, 330 + 85 + j * 110), line, font=font, fill="#222", anchor="mm")
        d.text((W - 40, H - 60), "AI 생성 콘텐츠", font=label_font, fill="white", anchor="rm", stroke_width=3, stroke_fill="#222")
        p = out_path.with_name(f"caption_{i}.png")
        img.save(p)
        overlays.append(p)

    inputs = ["-i", str(clip)]
    for p in overlays:
        inputs += ["-i", str(p)]
    chain = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[v0]"
    for i in range(len(beats)):
        a, b = i * per, (i + 1) * per
        chain += f";[v{i}][{i + 1}:v]overlay=enable='between(t,{a:.2f},{b:.2f})'[v{i + 1}]"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", chain,
        "-map", f"[v{len(beats)}]", "-map", "0:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-c:a", "aac", "-movflags", "+faststart", str(out_path),
    ]
    subprocess.run(cmd, check=True)
    for p in overlays:
        p.unlink()
    return out_path
