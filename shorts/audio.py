"""음성(TTS), 배경음악(직접 합성), 믹싱.

- 음성: edge-tts (무료, 한국어 신경망 음성). 안 되면 espeak-ng로 대체(테스트용).
- 배경음악: 매번 새로 합성하는 짧은 멜로디 → 저작권 걱정 없음, 영상마다 다름.
"""
from __future__ import annotations

import asyncio
import os
import random
import subprocess
import wave
from pathlib import Path

import numpy as np

from .characters import CAST

SR = 24000
GAP = 0.35  # 대사 사이 쉬는 시간(초)


def _decode(path: Path) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


async def _edge(text, voice, rate, pitch, out):
    import edge_tts
    proxy = os.environ.get("HTTPS_PROXY") or None
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, proxy=proxy).save(str(out))


def tts(text: str, char_key: str, out: Path) -> np.ndarray:
    ch = CAST[char_key]
    engine = os.environ.get("TTS_ENGINE", "edge")
    if engine == "edge":
        try:
            asyncio.run(_edge(text, ch.voice, ch.rate, ch.pitch, out))
            if out.exists() and out.stat().st_size > 0:
                return _decode(out)
        except Exception as e:  # 네트워크 차단 등
            print(f"[tts] edge-tts 실패 → espeak-ng 대체: {e.__class__.__name__}")
    pitch = {"dino": 75, "mochi": 60, "nyangu": 70, "boo": 80}.get(char_key, 60)
    wav = out.with_suffix(".wav")
    subprocess.run(["espeak-ng", "-v", "ko", "-s", "165", "-p", str(pitch), "-w", str(wav), text], check=True)
    return _decode(wav)


# ---------------------------------------------------------------- 배경음악

def _note_freq(semi: int) -> float:
    return 440.0 * 2 ** ((semi - 9) / 12)  # 0 = C4 기준


def _pluck(freq, dur, vol=0.3, bright=0.3):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 5) * np.minimum(1, t * 200)
    w = np.sin(2 * np.pi * freq * t) + bright * np.sin(4 * np.pi * freq * t) + 0.1 * np.sin(6 * np.pi * freq * t)
    return (w * env * vol).astype(np.float32)


def music(duration: float, seed: int) -> np.ndarray:
    rnd = random.Random(seed)
    bpm = rnd.choice([96, 104, 112, 120, 128])
    beat = 60 / bpm
    key = rnd.choice([0, 2, 5, 7, -3])
    scale = [0, 2, 4, 7, 9]  # 장조 펜타토닉: 밝고 귀여운 느낌
    progs = [[0, 7, 9, 5], [0, 5, 7, 0], [9, 5, 0, 7], [0, 9, 5, 7]]
    prog = rnd.choice(progs)
    n = int(SR * (duration + 1))
    out = np.zeros(n, dtype=np.float32)

    def add(sig, at):
        i = int(at * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        out[i:j] += sig[: j - i]

    # 4마디짜리 멜로디 패턴을 만들고 반복 (반복될 때 살짝 변주)
    motif = []
    deg = rnd.randint(0, 4)
    for _ in range(16):
        deg = max(0, min(9, deg + rnd.choice([-2, -1, 0, 1, 1, 2])))
        rest = rnd.random() < .2
        motif.append(None if rest else deg)
    t = 0.0
    bar = 0
    while t < duration + 1:
        root = prog[bar % 4] + key
        for b in range(4):  # 베이스 + 화음
            add(_pluck(_note_freq(root - 24), beat * .9, .22, .1), t + b * beat)
            if b % 2 == 1:
                for iv in (0, 4, 7):
                    add(_pluck(_note_freq(root + iv), beat * .5, .05, .2), t + b * beat)
        for k in range(4):  # 멜로디 (8분음표 x2 → 4개 사용)
            m = motif[(bar % 4) * 4 + k]
            if m is not None and not (bar >= 4 and rnd.random() < .15):
                semi = key + 12 + scale[m % 5] + 12 * (m // 5)
                add(_pluck(_note_freq(semi), beat * .9, .09, .45), t + k * beat)
        t += 4 * beat
        bar += 1
    out = out[: int(SR * duration)]
    fade = int(SR * 1.0)
    out[-fade:] *= np.linspace(1, 0, fade)
    peak = np.abs(out).max() or 1
    return out / peak * 0.16


def pop_sfx() -> np.ndarray:
    t = np.arange(int(SR * .12)) / SR
    f = 600 + 900 * t / .12
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30) * .25).astype(np.float32)


# ---------------------------------------------------------------- 조립

def build(script: dict, workdir: Path, fps: int, seed: int):
    """대사별 음성 생성 → 타이밍 계산 → 음악/효과음 믹스 → wav 저장."""
    workdir.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, sc in enumerate(script["scenes"]):
        clips.append(tts(sc["line"], sc["speaker"], workdir / f"line{i:02d}.mp3"))
    t = 0.5
    scenes = []
    for c in clips:
        dur = len(c) / SR + GAP
        hop = SR // fps
        rms = np.array([np.sqrt(np.mean(c[k:k + hop] ** 2)) if k < len(c) else 0 for k in range(0, int(dur * SR), hop)])
        rms = rms / (rms.max() or 1)
        scenes.append({"start": t, "dur": dur, "rms": rms})
        t += dur
    total = t + 0.6
    voice = np.zeros(int(SR * total) + SR, dtype=np.float32)
    sfx = pop_sfx()
    for c, s in zip(clips, scenes):
        i = int(s["start"] * SR)
        voice[i:i + len(c)] += c
        voice[max(0, i - len(sfx)):i] += sfx[: i - max(0, i - len(sfx))]
    voice = voice[: int(SR * total)]
    mix = voice * 0.95 + music(total, seed)
    mix = np.clip(mix, -1, 1)
    path = workdir / "mix.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return path, scenes
