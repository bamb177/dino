"""밈 영상 한 편 만들기 (업로드는 --publish 를 줄 때만).

예)
  python run.py                          # 영상만 생성 -> out/<시각>/
  python run.py --topic "점심 메뉴 고르기"
  python run.py --publish youtube        # 생성 후 유튜브에 '비공개'로 업로드
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml

from pipeline.render import render_video
from pipeline.script import generate_script

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--character", default="dino")
    p.add_argument("--topic")
    p.add_argument("--publish", choices=["none", "youtube", "instagram", "both"], default="none")
    p.add_argument("--youtube-privacy", choices=["private", "unlisted", "public"], default="private")
    p.add_argument("--video-url", help="인스타그램 업로드용 공개 영상 URL")
    args = p.parse_args()

    character = yaml.safe_load((ROOT / "character" / f"{args.character}.yaml").read_text())
    script = generate_script(character, args.topic)

    out_dir = ROOT / "out" / datetime.now().strftime("%Y%m%d-%H%M%S")
    video = render_video(script, character, out_dir / "video.mp4", ROOT / "character" / f"{args.character}.png")
    meta = {"script": script, "video": str(video.relative_to(ROOT)), "uploads": {}}

    if args.publish in ("youtube", "both"):
        from pipeline import upload_youtube
        meta["uploads"]["youtube"] = upload_youtube.upload(video, script, args.youtube_privacy)
    if args.publish in ("instagram", "both"):
        if not args.video_url:
            raise SystemExit("인스타그램 업로드에는 --video-url (공개 URL) 이 필요합니다.")
        from pipeline import upload_instagram
        meta["uploads"]["instagram"] = upload_instagram.upload(args.video_url, script)

    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
