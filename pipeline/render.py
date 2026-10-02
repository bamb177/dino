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
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    body, belly, cheek = colors["body"], colors["belly"], colors["cheek"]
    s = size / 700
    # 꼬리, 몸, 배
    d.polygon([(120 * s, 520 * s), (20 * s, 600 * s), (200 * s, 580 * s)], fill=body)
    d.ellipse([130 * s, 330 * s, 570 * s, 680 * s], fill=body)
    d.ellipse([230 * s, 430 * s, 470 * s, 670 * s], fill=belly)
    # 등 가시
    for x in (200, 280, 360):
        d.polygon([(x * s, 250 * s), ((x + 40) * s, 180 * s), ((x + 80) * s, 250 * s)], fill="#5FAF55")
    # 머리
    d.ellipse([150 * s, 120 * s, 550 * s, 470 * s], fill=body)
    # 눈
    eye_y = 260 * s
    for ex in (270 * s, 430 * s):
        if mood == "happy":
            d.arc([ex - 35 * s, eye_y - 25 * s, ex + 35 * s, eye_y + 35 * s], 200, 340, fill="#222", width=int(10 * s))
        elif mood == "shock":
            d.ellipse([ex - 40 * s, eye_y - 40 * s, ex + 40 * s, eye_y + 40 * s], fill="white", outline="#222", width=int(6 * s))
            d.ellipse([ex - 12 * s, eye_y - 12 * s, ex + 12 * s, eye_y + 12 * s], fill="#222")
        else:
            d.ellipse([ex - 30 * s, eye_y - 34 * s, ex + 30 * s, eye_y + 34 * s], fill="#222")
            d.ellipse([ex - 4 * s, eye_y - 24 * s, ex + 14 * s, eye_y - 6 * s], fill="white")
        if mood == "sad":
            d.ellipse([ex + 10 * s, eye_y + 40 * s, ex + 30 * s, eye_y + 75 * s], fill="#7EC8F5")
    # 볼터치
    for cx in (215 * s, 485 * s):
        d.ellipse([cx - 35 * s, 320 * s, cx + 35 * s, 360 * s], fill=cheek)
    # 입
    mx, my = 350 * s, 360 * s
    if mood == "shock":
        d.ellipse([mx - 25 * s, my - 10 * s, mx + 25 * s, my + 45 * s], fill="#6B2E2E")
    elif mood == "sad":
        d.arc([mx - 30 * s, my + 5 * s, mx + 30 * s, my + 45 * s], 200, 340, fill="#222", width=int(7 * s))
    else:
        d.arc([mx - 30 * s, my - 25 * s, mx + 30 * s, my + 20 * s], 20, 160, fill="#222", width=int(7 * s))
    # 팔, 발
    d.ellipse([140 * s, 470 * s, 210 * s, 540 * s], fill=body)
    d.ellipse([490 * s, 470 * s, 560 * s, 540 * s], fill=body)
    d.ellipse([200 * s, 630 * s, 310 * s, 690 * s], fill="#5FAF55")
    d.ellipse([390 * s, 630 * s, 500 * s, 690 * s], fill="#5FAF55")
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
