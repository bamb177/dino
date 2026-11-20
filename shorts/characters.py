"""오리지널 캐릭터 드로잉.

모든 캐릭터는 코드로 직접 그립니다(외부 이미지/밈 사용 없음 → 저작권 걱정 없음).
스프라이트는 2배 크기로 그린 뒤 축소해서 계단 현상 없이 부드럽게 보이게 합니다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

from PIL import Image, ImageDraw

SS = 2  # supersampling 배율
SPRITE = 640  # 최종 스프라이트 한 변(px)

EMOTIONS = ["happy", "sad", "surprised", "angry", "love", "sleepy", "neutral", "smug"]


@dataclass(frozen=True)
class Character:
    key: str
    name: str
    kind: str  # dino | mochi | cat | ghost
    body: tuple
    belly: tuple
    accent: tuple
    personality: str
    voice: str
    pitch: str = "+0Hz"
    rate: str = "+0%"
    tag_color: tuple = (255, 255, 255)


CAST: dict[str, Character] = {
    "dino": Character(
        key="dino", name="디노", kind="dino",
        body=(126, 214, 170), belly=(214, 246, 222), accent=(255, 170, 120),
        personality="호기심 많고 엉뚱한 아기 공룡. 뭐든 먹어보려고 하고 실수가 많지만 해맑다.",
        voice="ko-KR-SunHiNeural", pitch="+30Hz", rate="+8%", tag_color=(70, 170, 120),
    ),
    "mochi": Character(
        key="mochi", name="모찌", kind="mochi",
        body=(255, 240, 244), belly=(255, 255, 255), accent=(140, 200, 120),
        personality="말랑말랑한 찹쌀떡. 느긋하고 잠이 많으며 다정한 말을 잘 한다.",
        voice="ko-KR-SunHiNeural", pitch="+12Hz", rate="-6%", tag_color=(230, 120, 150),
    ),
    "nyangu": Character(
        key="nyangu", name="냥구", kind="cat",
        body=(255, 196, 120), belly=(255, 236, 205), accent=(230, 140, 60),
        personality="새침한 고양이. 츤데레라 관심 없는 척하지만 사실 다 챙겨준다.",
        voice="ko-KR-InJoonNeural", pitch="+40Hz", rate="+4%", tag_color=(220, 130, 50),
    ),
    "boo": Character(
        key="boo", name="부부", kind="ghost",
        body=(205, 196, 255), belly=(232, 228, 255), accent=(150, 130, 240),
        personality="겁 많은 꼬마 유령. 자기가 유령인데 무서운 걸 제일 싫어한다.",
        voice="ko-KR-HyunsuNeural", pitch="+35Hz", rate="+2%", tag_color=(130, 110, 220),
    ),
}

OUTLINE = (60, 46, 52)


def _shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


# ---------------------------------------------------------------- 몸통

def _body_dino(d: ImageDraw.ImageDraw, W: int, ch: Character):
    o = 10 * SS
    # 꼬리
    d.polygon([(W * .70, W * .78), (W * .97, W * .70), (W * .74, W * .90)], fill=ch.body, outline=OUTLINE, width=o)
    # 등 가시
    for i, (x, y) in enumerate([(.33, .20), (.47, .13), (.61, .16), (.73, .26)]):
        s = W * .075
        cx, cy = W * x, W * y
        d.polygon([(cx - s, cy + s * .9), (cx, cy - s), (cx + s, cy + s * .9)], fill=ch.accent, outline=OUTLINE, width=o)
    # 몸
    d.ellipse([W * .16, W * .16, W * .84, W * .95], fill=ch.body, outline=OUTLINE, width=o)
    d.ellipse([W * .30, W * .56, W * .70, W * .93], fill=ch.belly)
    # 팔
    d.ellipse([W * .15, W * .58, W * .27, W * .70], fill=ch.body, outline=OUTLINE, width=o)
    d.ellipse([W * .73, W * .58, W * .85, W * .70], fill=ch.body, outline=OUTLINE, width=o)
    # 발
    d.ellipse([W * .27, W * .86, W * .43, W * .97], fill=_shade(ch.body, .9), outline=OUTLINE, width=o)
    d.ellipse([W * .57, W * .86, W * .73, W * .97], fill=_shade(ch.body, .9), outline=OUTLINE, width=o)
    return W * .5, W * .43, W * .30


def _body_mochi(d, W, ch):
    o = 10 * SS
    d.ellipse([W * .08, W * .30, W * .92, W * .95], fill=ch.body, outline=OUTLINE, width=o)
    # 잎사귀
    d.ellipse([W * .46, W * .17, W * .66, W * .33], fill=ch.accent, outline=OUTLINE, width=o)
    d.line([(W * .50, W * .31), (W * .60, W * .21)], fill=OUTLINE, width=o // 2)
    return W * .5, W * .58, W * .34


def _body_cat(d, W, ch):
    o = 10 * SS
    # 귀
    d.polygon([(W * .18, W * .36), (W * .22, W * .08), (W * .44, W * .24)], fill=ch.body, outline=OUTLINE, width=o)
    d.polygon([(W * .82, W * .36), (W * .78, W * .08), (W * .56, W * .24)], fill=ch.body, outline=OUTLINE, width=o)
    d.polygon([(W * .24, W * .30), (W * .25, W * .16), (W * .36, W * .25)], fill=(255, 170, 170))
    d.polygon([(W * .76, W * .30), (W * .75, W * .16), (W * .64, W * .25)], fill=(255, 170, 170))
    # 꼬리
    d.arc([W * .62, W * .50, W * 1.0, W * .95], 250, 40, fill=OUTLINE, width=int(W * .07))
    d.arc([W * .62, W * .50, W * 1.0, W * .95], 250, 40, fill=ch.accent, width=int(W * .045))
    d.ellipse([W * .12, W * .18, W * .88, W * .95], fill=ch.body, outline=OUTLINE, width=o)
    # 줄무늬
    for x in (.42, .50, .58):
        d.line([(W * x, W * .20), (W * x, W * .29)], fill=ch.accent, width=int(W * .025))
    d.ellipse([W * .32, W * .62, W * .68, W * .93], fill=ch.belly)
    return W * .5, W * .48, W * .30


def _body_ghost(d, W, ch):
    o = 10 * SS
    top, bottom = W * .12, W * .86
    pts = []
    for i in range(0, 181, 6):
        a = math.radians(180 + i)
        pts.append((W * .5 + math.cos(a) * W * .36, W * .46 + math.sin(a) * W * .34))
    waves = 4
    for i in range(waves * 8 + 1):
        x = W * .86 - (W * .72) * i / (waves * 8)
        y = bottom + math.sin(i / 8 * 2 * math.pi) * W * .04
        pts.append((x, y))
    d.polygon(pts, fill=ch.body, outline=OUTLINE, width=o)
    # 팔
    d.ellipse([W * .06, W * .50, W * .20, W * .62], fill=ch.body, outline=OUTLINE, width=o)
    d.ellipse([W * .80, W * .50, W * .94, W * .62], fill=ch.body, outline=OUTLINE, width=o)
    return W * .5, W * .47, W * .32


BODIES = {"dino": _body_dino, "mochi": _body_mochi, "cat": _body_cat, "ghost": _body_ghost}


# ---------------------------------------------------------------- 얼굴

def _heart(d, cx, cy, s, fill):
    d.ellipse([cx - s, cy - s * .6, cx, cy + s * .4], fill=fill)
    d.ellipse([cx, cy - s * .6, cx + s, cy + s * .4], fill=fill)
    d.polygon([(cx - s * .97, cy), (cx + s * .97, cy), (cx, cy + s * 1.05)], fill=fill)


def _face(d: ImageDraw.ImageDraw, cx, cy, r, emotion: str, mouth: int, blink: bool):
    ex = r * .55
    ey = cy - r * .05
    er = r * .17
    lw = int(r * .07)
    eyes = []
    for sx in (-1, 1):
        x = cx + sx * ex
        if blink or emotion == "sleepy":
            d.arc([x - er, ey - er * .4, x + er, ey + er * .9], 200, 340, fill=OUTLINE, width=lw)
        elif emotion == "happy":
            d.arc([x - er, ey - er * .2, x + er, ey + er * 1.6], 200, 340, fill=OUTLINE, width=lw)
        elif emotion == "smug":
            d.line([(x - er, ey), (x + er, ey)], fill=OUTLINE, width=lw)
            d.chord([x - er, ey - er * .3, x + er, ey + er * 1.2], 0, 180, fill=OUTLINE)
        elif emotion == "love":
            _heart(d, x, ey, er * 1.25, (240, 70, 110))
        elif emotion == "surprised":
            d.ellipse([x - er * 1.1, ey - er * 1.3, x + er * 1.1, ey + er * 1.3], fill=(255, 255, 255), outline=OUTLINE, width=lw)
            d.ellipse([x - er * .45, ey - er * .45, x + er * .45, ey + er * .45], fill=OUTLINE)
        else:
            d.ellipse([x - er, ey - er * 1.2, x + er, ey + er * 1.2], fill=OUTLINE)
            d.ellipse([x - er * .55, ey - er * .9, x - er * .05, ey - er * .3], fill=(255, 255, 255))
            d.ellipse([x + er * .15, ey + er * .2, x + er * .45, ey + er * .55], fill=(255, 255, 255))
        eyes.append(x)
        if emotion == "angry":
            d.line([(x - sx * er * 1.3, ey - er * 2.0), (x + sx * er * 1.1, ey - er * 1.3)], fill=OUTLINE, width=lw)
        if emotion == "sad":
            d.line([(x - sx * er * 1.2, ey - er * 1.4), (x + sx * er * 1.0, ey - er * 2.0)], fill=OUTLINE, width=lw)
    # 볼터치
    for sx in (-1, 1):
        bx = cx + sx * r * .82
        d.ellipse([bx - r * .17, ey + r * .22, bx + r * .17, ey + r * .38], fill=(255, 150, 170))
    if emotion == "sad":
        x = eyes[0]
        d.ellipse([x - er * .5, ey + er * 1.4, x + er * .5, ey + er * 2.6], fill=(120, 190, 255))
    # 입
    my = cy + r * .35
    mw = r * .22
    if mouth == 0:
        if emotion in ("sad", "angry"):
            d.arc([cx - mw, my, cx + mw, my + mw * 1.2], 200, 340, fill=OUTLINE, width=lw)
        elif emotion == "surprised":
            d.ellipse([cx - mw * .45, my - mw * .2, cx + mw * .45, my + mw * .7], fill=OUTLINE)
        else:
            # ω 모양 입
            d.arc([cx - mw, my - mw * .6, cx, my + mw * .4], 0, 180, fill=OUTLINE, width=lw)
            d.arc([cx, my - mw * .6, cx + mw, my + mw * .4], 0, 180, fill=OUTLINE, width=lw)
    else:
        h = mw * (0.55 if mouth == 1 else 1.0)
        d.chord([cx - mw * .8, my - h * .5, cx + mw * .8, my + h * 1.1], 0, 180, fill=(120, 40, 60), outline=OUTLINE, width=lw // 2)
        d.ellipse([cx - mw * .4, my + h * .25, cx + mw * .4, my + h * .95], fill=(255, 120, 140))


@lru_cache(maxsize=512)
def sprite(key: str, emotion: str, mouth: int, blink: bool) -> Image.Image:
    ch = CAST[key]
    W = SPRITE * SS
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy, r = BODIES[ch.kind](d, W, ch)
    _face(d, cx, cy, r, emotion if emotion in EMOTIONS else "neutral", mouth, blink)
    return img.resize((SPRITE, SPRITE), Image.LANCZOS)


if __name__ == "__main__":  # 캐릭터 시트 미리보기
    sheet = Image.new("RGB", (SPRITE * len(EMOTIONS) // 2, SPRITE * len(CAST)), (250, 245, 235))
    for row, k in enumerate(CAST):
        for col, e in enumerate(EMOTIONS):
            sp = sprite(k, e, 1 if col % 3 == 0 else 0, False).resize((SPRITE // 2, SPRITE // 2))
            sheet.paste(sp, (col * SPRITE // 2, row * SPRITE), sp)
    sheet.save("character_sheet.png")
    print("saved character_sheet.png")
