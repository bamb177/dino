"""대본 -> 9:16 세로 영상(mp4). 유료 API 없이 Pillow + ffmpeg 로 렌더링합니다.

character/dino.png 가 있으면 그 이미지를 캐릭터로 쓰고(AI 이미지나 site/ 의 그림 추출기로 만든 PNG),
없으면 코드로 그린 기본 아기 공룡을 씁니다.
"""
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30
BEAT_SECONDS = 3.0

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError("한글 폰트가 없습니다. fonts-noto-cjk 를 설치하세요.")


def draw_default_dino(colors: dict, mood: str, size: int = 700) -> Image.Image:
    """사람처럼 두 발로 서 있는 공룡: 큰 머리, 셔츠+넥타이, 바지, 구두."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    body, cheek = colors["body"], colors["cheek"]
    shirt, tie, pants = colors.get("shirt", "#fff"), colors.get("tie", "#E8505B"), colors.get("pants", "#4A5A7A")
    dark = "#5FAF55"
    s = size / 700

    def P(*pts):
        return [(x * s, y * s) for x, y in pts]

    # 꼬리
    d.polygon(P((235, 470), (110, 560), (150, 590), (260, 530)), fill=body)
    # 다리 + 구두
    for x in (265, 385):
        d.rectangle([x * s, 520 * s, (x + 55) * s, 640 * s], fill=pants)
        d.rounded_rectangle([(x - 15) * s, 625 * s, (x + 80) * s, 675 * s], radius=int(20 * s), fill="#3A2E2E")
    # 몸통(셔츠)
    d.rounded_rectangle([225 * s, 355 * s, 475 * s, 540 * s], radius=int(40 * s), fill=shirt, outline="#BBB", width=int(3 * s))
    d.rectangle([225 * s, 500 * s, 475 * s, 540 * s], fill=pants)
    # 넥타이
    d.polygon(P((350, 365), (330, 385), (340, 395), (325, 470), (350, 495), (375, 470), (360, 395), (370, 385)), fill=tie)
    # 팔
    d.rounded_rectangle([180 * s, 370 * s, 232 * s, 500 * s], radius=int(25 * s), fill=shirt, outline="#BBB", width=int(3 * s))
    d.rounded_rectangle([468 * s, 370 * s, 520 * s, 500 * s], radius=int(25 * s), fill=shirt, outline="#BBB", width=int(3 * s))
    for hx in (206, 494):
        d.ellipse([(hx - 28) * s, 485 * s, (hx + 28) * s, 540 * s], fill=body)
    # 등 가시 + 머리
    for x in (240, 310, 380):
        d.polygon(P((x, 105), (x + 35, 40), (x + 70, 105)), fill=dark)
    d.ellipse([160 * s, 70 * s, 540 * s, 400 * s], fill=body)
    # 눈
    eye_y = 220 * s
    for ex in (280 * s, 420 * s):
        if mood == "happy":
            d.arc([ex - 32 * s, eye_y - 22 * s, ex + 32 * s, eye_y + 32 * s], 200, 340, fill="#222", width=int(9 * s))
        elif mood == "shock":
            d.ellipse([ex - 38 * s, eye_y - 38 * s, ex + 38 * s, eye_y + 38 * s], fill="white", outline="#222", width=int(6 * s))
            d.ellipse([ex - 11 * s, eye_y - 11 * s, ex + 11 * s, eye_y + 11 * s], fill="#222")
        else:
            d.ellipse([ex - 28 * s, eye_y - 32 * s, ex + 28 * s, eye_y + 32 * s], fill="#222")
            d.ellipse([ex - 4 * s, eye_y - 22 * s, ex + 12 * s, eye_y - 6 * s], fill="white")
        if mood == "sad":
            d.ellipse([ex + 8 * s, eye_y + 38 * s, ex + 28 * s, eye_y + 72 * s], fill="#7EC8F5")
    for cx in (225 * s, 475 * s):
        d.ellipse([cx - 32 * s, 275 * s, cx + 32 * s, 312 * s], fill=cheek)
    mx, my = 350 * s, 315 * s
    if mood == "shock":
        d.ellipse([mx - 22 * s, my - 8 * s, mx + 22 * s, my + 40 * s], fill="#6B2E2E")
    elif mood == "sad":
        d.arc([mx - 28 * s, my + 5 * s, mx + 28 * s, my + 42 * s], 200, 340, fill="#222", width=int(7 * s))
    else:
        d.arc([mx - 28 * s, my - 22 * s, mx + 28 * s, my + 18 * s], 20, 160, fill="#222", width=int(7 * s))
    return img


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split(" "):
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) > max_width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def render_video(script: dict, character: dict, out_path: Path, char_png: Path | None = None) -> Path:
    colors = character["colors"]
    caption_font = load_font(78)
    title_font = load_font(54)
    label_font = load_font(34)
    custom = Image.open(char_png).convert("RGBA").resize((700, 700)) if char_png and char_png.exists() else None

    beats = script["beats"]
    frames_per_beat = int(BEAT_SECONDS * FPS)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-movflags", "+faststart", str(out_path),
        ],
        stdin=subprocess.PIPE,
    )

    for i, beat in enumerate(beats):
        dino = custom if custom else draw_default_dino(colors, beat["mood"])
        for f in range(frames_per_beat):
            t = f / FPS
            frame = Image.new("RGB", (W, H), colors["background"])
            d = ImageDraw.Draw(frame)

            d.text((W / 2, 170), script["title"], font=title_font, fill="#555", anchor="mm")

            # 자막 박스 (팝업 효과)
            pop = min(1.0, t / 0.15)
            lines = wrap_text(d, beat["caption"], caption_font, W - 160)
            box_h = 110 * len(lines) + 60
            top = 330
            d.rounded_rectangle([60, top, W - 60, top + box_h], radius=40, fill="white", outline="#222", width=6)
            if pop >= 1.0:
                for j, line in enumerate(lines):
                    d.text((W / 2, top + 85 + j * 110), line, font=caption_font, fill="#222", anchor="mm")

            # 캐릭터: 둥실둥실 / 충격이면 흔들림
            bob = math.sin(t * 2 * math.pi * 1.2) * 18
            shake = math.sin(t * 60) * 12 if beat["mood"] == "shock" and t < 0.6 else 0
            frame.paste(dino, (int((W - 700) / 2 + shake), int(1000 + bob)), dino)

            # 진행 표시 + AI 생성 표기
            d.rectangle([0, H - 12, W * (i * frames_per_beat + f) / (len(beats) * frames_per_beat), H], fill="#7BC96F")
            d.text((W - 40, H - 60), "AI 생성 콘텐츠", font=label_font, fill="#888", anchor="rm")

            ffmpeg.stdin.write(frame.tobytes())

    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise RuntimeError("ffmpeg 인코딩 실패")
    return out_path
