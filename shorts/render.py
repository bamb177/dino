"""대본(JSON) + 음성 → 1080x1920 세로 영상 렌더링.

프레임을 Pillow로 그려서 ffmpeg 파이프로 바로 인코딩합니다.
"""
from __future__ import annotations

import math
import random
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .characters import CAST, SPRITE, sprite

W, H = 1080, 1920
FPS = 30

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
]


@lru_cache(maxsize=16)
def font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            idx = 1 if p.endswith("NotoSansCJK-Bold.ttc") else 0  # 1 = KR
            return ImageFont.truetype(p, size, index=idx)
    raise RuntimeError("한글 폰트를 찾지 못했어요. fonts-noto-cjk 를 설치하세요.")


# ---------------------------------------------------------------- 배경

BACKGROUNDS = ["room", "park", "night", "beach", "snow", "kitchen", "cafe", "space"]


def _grad(top, bottom):
    a = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top)[None, None, :] * (1 - a) + np.array(bottom)[None, None, :] * a)
    arr = np.repeat(arr, W, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _cloud(d, x, y, s, c=(255, 255, 255)):
    for dx, dy, r in [(0, 0, 1), (-.9, .25, .7), (.9, .25, .75), (.4, -.4, .7)]:
        d.ellipse([x + dx * s - r * s, y + dy * s - r * s, x + dx * s + r * s, y + dy * s + r * s], fill=c)


@lru_cache(maxsize=32)
def background(kind: str, seed: int) -> Image.Image:
    rnd = random.Random(seed)
    hue = rnd.uniform(-12, 12)

    def j(c):  # 약간의 색 변주
        return tuple(int(max(0, min(255, v + hue * (i - 1)))) for i, v in enumerate(c))

    floor_y = 1270
    if kind == "park":
        img = _grad(j((150, 210, 255)), j((220, 240, 255)))
        d = ImageDraw.Draw(img)
        d.ellipse([760, 120, 960, 320], fill=(255, 226, 120))
        for _ in range(4):
            _cloud(d, rnd.randint(80, 1000), rnd.randint(150, 600), rnd.randint(50, 80))
        d.ellipse([-300, floor_y - 160, 700, floor_y + 500], fill=j((150, 215, 120)))
        d.ellipse([400, floor_y - 120, 1400, floor_y + 500], fill=j((130, 200, 105)))
        d.rectangle([0, floor_y + 60, W, H], fill=j((120, 190, 95)))
        for _ in range(30):
            x, y = rnd.randint(0, W), rnd.randint(floor_y + 80, H)
            d.ellipse([x, y, x + 14, y + 14], fill=rnd.choice([(255, 255, 255), (255, 200, 220), (255, 240, 140)]))
    elif kind == "night":
        img = _grad(j((30, 30, 80)), j((90, 70, 150)))
        d = ImageDraw.Draw(img)
        for _ in range(90):
            x, y, s = rnd.randint(0, W), rnd.randint(0, 1200), rnd.choice([2, 3, 4, 6])
            d.ellipse([x, y, x + s, y + s], fill=(255, 255, 230))
        d.ellipse([720, 160, 940, 380], fill=(255, 245, 200))
        d.ellipse([780, 140, 1000, 360], fill=j((40, 38, 92)))
        d.rectangle([0, floor_y + 40, W, H], fill=j((50, 60, 110)))
    elif kind == "beach":
        img = _grad(j((120, 200, 255)), j((200, 240, 255)))
        d = ImageDraw.Draw(img)
        d.ellipse([120, 150, 320, 350], fill=(255, 220, 110))
        _cloud(d, 800, 300, 70)
        d.rectangle([0, 1000, W, floor_y + 60], fill=j((70, 170, 230)))
        for i in range(6):
            y = 1040 + i * 40
            d.arc([rnd.randint(-50, 900), y, rnd.randint(1000, 1300), y + 40], 200, 340, fill=(220, 245, 255), width=5)
        d.rectangle([0, floor_y + 60, W, H], fill=j((250, 225, 170)))
    elif kind == "snow":
        img = _grad(j((190, 215, 245)), j((235, 245, 255)))
        d = ImageDraw.Draw(img)
        for x in (120, 940):
            d.polygon([(x - 110, 1180), (x, 820), (x + 110, 1180)], fill=j((80, 150, 120)))
            d.polygon([(x - 80, 960), (x, 820), (x + 80, 960)], fill=(255, 255, 255))
        d.rectangle([0, floor_y + 40, W, H], fill=(250, 252, 255))
        d.ellipse([-200, floor_y - 30, 600, floor_y + 160], fill=(250, 252, 255))
    elif kind == "kitchen":
        img = Image.new("RGB", (W, H), j((255, 246, 228)))
        d = ImageDraw.Draw(img)
        for y in range(0, floor_y, 90):
            for x in range((y // 90 % 2) * 45, W, 90):
                d.rectangle([x, y, x + 86, y + 86], fill=j((250, 236, 210)))
        d.rectangle([0, floor_y - 40, W, floor_y + 40], fill=j((200, 150, 110)))
        d.rectangle([0, floor_y + 40, W, H], fill=j((230, 200, 165)))
        d.rounded_rectangle([700, 300, 980, 620], 30, fill=(255, 255, 255), outline=(220, 200, 180), width=8)
    elif kind == "cafe":
        img = _grad(j((255, 225, 200)), j((240, 200, 170)))
        d = ImageDraw.Draw(img)
        for i in range(5):
            x = 80 + i * 220
            d.line([(x, 0), (x, 160)], fill=(120, 90, 70), width=4)
            d.chord([x - 50, 140, x + 50, 240], 180, 360, fill=(255, 235, 160))
        d.rectangle([0, floor_y + 40, W, H], fill=j((170, 120, 90)))
        for x in range(0, W, 120):
            d.line([(x, floor_y + 40), (x, H)], fill=j((150, 105, 80)), width=4)
    elif kind == "space":
        img = _grad(j((15, 10, 40)), j((60, 30, 90)))
        d = ImageDraw.Draw(img)
        for _ in range(140):
            x, y, s = rnd.randint(0, W), rnd.randint(0, H), rnd.choice([2, 3, 5])
            d.ellipse([x, y, x + s, y + s], fill=(255, 255, 255))
        d.ellipse([650, 250, 1000, 600], fill=j((255, 170, 120)))
        d.arc([560, 380, 1090, 470], 160, 380, fill=(255, 230, 180), width=14)
        d.ellipse([-200, floor_y + 20, W + 200, H + 600], fill=j((170, 160, 190)))
    else:  # room
        img = Image.new("RGB", (W, H), j((255, 236, 220)))
        d = ImageDraw.Draw(img)
        for x in range(0, W, 80):
            d.rectangle([x, 0, x + 38, floor_y], fill=j((255, 228, 210)))
        d.rounded_rectangle([110, 260, 470, 660], 24, fill=(170, 220, 255), outline=(255, 255, 255), width=18)
        d.line([(290, 260), (290, 660)], fill=(255, 255, 255), width=12)
        d.rectangle([0, floor_y + 40, W, H], fill=j((215, 175, 140)))
        d.ellipse([200, floor_y + 160, 880, floor_y + 360], fill=j((255, 200, 210)))
    return img


# ---------------------------------------------------------------- 효과

def _star(d, cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * .45
        pts.append((cx + math.cos(a) * rr, cy - math.sin(a) * rr))
    d.polygon(pts, fill=fill)


def _heart(d, cx, cy, s, fill):
    d.ellipse([cx - s, cy - s * .6, cx, cy + s * .4], fill=fill)
    d.ellipse([cx, cy - s * .6, cx + s, cy + s * .4], fill=fill)
    d.polygon([(cx - s * .97, cy), (cx + s * .97, cy), (cx, cy + s * 1.05)], fill=fill)


def draw_effect(d, effect: str, t: float, anchor: tuple, rnd_seed: int):
    ax, ay = anchor
    rnd = random.Random(rnd_seed)
    if effect == "hearts":
        for i in range(6):
            ph = (t * .6 + i / 6) % 1
            x = ax + rnd.uniform(-240, 240) + math.sin(ph * 6 + i) * 20
            y = ay + 40 - ph * 480
            _heart(d, x, y, 26 + i % 3 * 8, (255, 100, 140))
    elif effect == "sparkles":
        for i in range(8):
            x, y = ax + rnd.uniform(-300, 300), ay + rnd.uniform(-200, 30)
            s = abs(math.sin(t * 4 + i)) * 26 + 6
            _star(d, x, y, s, (255, 230, 90))
    elif effect == "rain":
        for i in range(70):
            x = (rnd.uniform(0, W) + t * 60) % W
            y = (rnd.uniform(0, H) + t * 1400) % H
            d.line([(x, y), (x - 8, y + 40)], fill=(150, 190, 255), width=4)
    elif effect == "snow":
        for i in range(60):
            x = (rnd.uniform(0, W) + math.sin(t + i) * 30) % W
            y = (rnd.uniform(0, H) + t * 160) % H
            s = rnd.choice([6, 9, 12])
            d.ellipse([x, y, x + s, y + s], fill=(255, 255, 255))
    elif effect == "sweat":
        y = ay + 60 + (t * 120) % 60
        d.ellipse([ax + 190, y, ax + 230, y + 56], fill=(140, 200, 255))
    elif effect == "zzz":
        for i in range(3):
            ph = (t * .5 + i / 3) % 1
            d.text((ax + 150 + ph * 120, ay - 40 - ph * 220), "Z", font=font(40 + i * 18), fill=(110, 110, 170))
    elif effect == "question":
        d.text((ax + 170, ay - 170 + math.sin(t * 5) * 10), "?", font=font(130), fill=(255, 150, 60), stroke_width=6, stroke_fill=(255, 255, 255))
    elif effect == "exclaim":
        s = 1 + .15 * abs(math.sin(t * 8))
        d.text((ax + 170, ay - 190), "!", font=font(int(140 * s)), fill=(255, 80, 80), stroke_width=6, stroke_fill=(255, 255, 255))
    elif effect == "confetti":
        cols = [(255, 120, 150), (120, 200, 255), (255, 220, 90), (140, 220, 150), (200, 150, 255)]
        for i in range(60):
            x = rnd.uniform(0, W) + math.sin(t * 2 + i) * 40
            y = (rnd.uniform(-H, 0) + t * 500) % H
            d.rectangle([x, y, x + 16, y + 26], fill=cols[i % len(cols)])
    elif effect == "music":
        for i in range(4):
            ph = (t * .5 + i / 4) % 1
            d.text((ax - 300 + i * 160, ay - 120 - ph * 200), "♪", font=font(70), fill=(255, 140, 180))


# ---------------------------------------------------------------- 텍스트

def wrap(text: str, f, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split(" "):
        test = (cur + " " + word).strip()
        if f.getlength(test) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            while f.getlength(word) > max_w:  # 공백 없는 긴 단어
                k = len(word)
                while f.getlength(word[:k]) > max_w:
                    k -= 1
                lines.append(word[:k])
                word = word[k:]
            cur = word
    if cur:
        lines.append(cur)
    return lines


@lru_cache(maxsize=64)
def subtitle_card(text: str, name: str, color: tuple) -> Image.Image:
    f = font(62)
    lines = wrap(text, f, 860)
    lh = 84
    bw, bh = 960, 70 + lh * len(lines)
    img = Image.new("RGBA", (bw, bh + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 46, bw - 6, bh + 44], 40, fill=(0, 0, 0, 60))
    d.rounded_rectangle([0, 36, bw - 6, bh + 36], 40, fill=(255, 255, 255, 245), outline=color, width=8)
    nf = font(42)
    nw = nf.getlength(name) + 56
    d.rounded_rectangle([36, 0, 36 + nw, 66], 33, fill=color)
    d.text((36 + 28, 8), name, font=nf, fill=(255, 255, 255))
    for i, ln in enumerate(lines):
        lw = f.getlength(ln)
        d.text(((bw - lw) / 2, 36 + 38 + i * lh), ln, font=f, fill=(55, 45, 50))
    return img


@lru_cache(maxsize=8)
def hook_banner(text: str) -> Image.Image:
    f = font(82)
    lines = wrap(text, f, 940)[:2]
    img = Image.new("RGBA", (W, 130 * len(lines) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        lw = f.getlength(ln)
        d.text(((W - lw) / 2, 20 + i * 120), ln, font=f, fill=(255, 255, 255), stroke_width=12, stroke_fill=(60, 46, 52))
    return img


# ---------------------------------------------------------------- 렌더

def _slots(n: int):
    if n == 1:
        return [(W // 2, 1310, 1.1)]
    return [(275, 1310, .76), (805, 1310, .76)]


def render(script: dict, scenes_audio: list[dict], audio_path: Path, out_path: Path, seed: int = 0):
    """scenes_audio: [{start, dur, rms(np.ndarray per frame)}] 대본 scenes와 같은 순서."""
    total = scenes_audio[-1]["start"] + scenes_audio[-1]["dur"] + 0.6
    nframes = int(total * FPS)
    cast = script["cast"]
    slots = {k: s for k, s in zip(cast, _slots(len(cast)))}
    hook = hook_banner(script.get("hook", ""))

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    blink_offsets = {k: random.Random(seed + i).uniform(0, 3) for i, k in enumerate(cast)}

    si = 0
    for fi in range(nframes):
        t = fi / FPS
        while si + 1 < len(scenes_audio) and t >= scenes_audio[si + 1]["start"]:
            si += 1
        sc = script["scenes"][si]
        sa = scenes_audio[si]
        lt = max(0.0, t - sa["start"])  # 장면 내 시간
        frame = background(sc.get("background", script.get("background", "room")), seed + si // 3).copy()
        d = ImageDraw.Draw(frame)

        # 캐릭터
        for k in cast:
            cx, by, sc_mul = slots[k]
            speaking = (k == sc["speaker"])
            emo = sc.get("emotion", "happy") if speaking else sc.get("listener_emotion", "neutral")
            lf = int(lt * FPS)
            amp = float(sa["rms"][lf]) if speaking and 0 <= lf < len(sa["rms"]) else 0.0
            mouth = 0 if amp < .12 else (1 if amp < .45 else 2)
            bt = (t + blink_offsets[k]) % 3.2
            blink = bt < .12
            sp = sprite(k, emo, mouth, blink)
            # 움직임
            bob_speed = {"happy": 2.4, "love": 2.0, "sad": .8, "sleepy": .6, "angry": 3.2}.get(emo, 1.4)
            bob = math.sin(t * bob_speed * math.pi) * (14 if speaking else 6)
            sy = 1 + .035 * math.sin(t * bob_speed * 2 * math.pi) + (amp * .05 if speaking else 0)
            sx = 2 - sy
            if speaking and lt < .25:  # 말 시작할 때 살짝 점프
                bob -= math.sin(lt / .25 * math.pi) * 40
            if emo == "angry" and speaking:
                cx += math.sin(t * 40) * 6
            size = int(SPRITE * sc_mul)
            w2, h2 = int(size * sx), int(size * sy)
            spr = sp.resize((w2, h2), Image.BILINEAR)
            frame.paste(spr, (int(cx - w2 / 2), int(by - h2 + bob)), spr)

        # 효과
        eff = sc.get("effect", "none")
        if eff and eff != "none":
            ax, ay, mul = slots.get(sc["speaker"], (W // 2, 1310, 1))
            draw_effect(d, eff, lt, (ax, ay - SPRITE * mul * .85), seed + si)

        # 상단 훅 문구
        frame.paste(hook, (0, 230), hook)

        # 자막 (팝 인)
        ch = CAST[sc["speaker"]]
        card = subtitle_card(sc["line"], ch.name, ch.tag_color)
        pop = min(1.0, lt / .15)
        scale = .85 + .15 * (1 - (1 - pop) ** 3)
        if scale < .999:
            card = card.resize((int(card.width * scale), int(card.height * scale)), Image.BILINEAR)
        frame.paste(card, ((W - card.width) // 2, 1500 - card.height // 2), card)

        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 인코딩 실패")
    return total
