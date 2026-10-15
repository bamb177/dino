"""밈 쇼츠 한 편 만들기. 매니저 Claude 가 소재 선정 -> 대본 -> 검수까지 하고, 승인된 경우에만 올립니다.

예)
  python run.py                          # 트렌드 수집 -> 대본 -> 영상 (업로드 안 함)
  python run.py --topic "점심 메뉴 고르기"
  python run.py --provider veo           # 영상 생성 AI(Veo) 사용 (GEMINI_API_KEY 필요, 유료)
  python run.py --publish youtube        # 매니저가 승인하면 유튜브에 업로드
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml

from pipeline import history, manager, trends
from pipeline.video_ai import make_video

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--character", default="dino")
    p.add_argument("--topic", help="주제를 직접 지정하면 트렌드 수집을 건너뜁니다")
    p.add_argument("--provider", choices=["local", "veo"], default="local")
    p.add_argument("--geo", default="KR", help="트렌드 국가 코드")
    p.add_argument("--publish", choices=["none", "youtube", "instagram", "both"], default="none")
    p.add_argument("--youtube-privacy", choices=["private", "unlisted", "public"], default="private")
    p.add_argument("--video-url", help="인스타그램 업로드용 공개 영상 URL")
    args = p.parse_args()

    character = yaml.safe_load((ROOT / "character" / f"{args.character}.yaml").read_text())
    found = [] if args.topic else trends.collect(args.geo)
    print(f"[trends] {len(found)}건 수집")
    script, approved, issues = manager.produce_script(found, character, args.topic)

    out_dir = ROOT / "out" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"script": script, "approved": approved, "issues": issues, "uploads": {}}

    if not approved:
        print("[manager] 3번 시도했지만 승인하지 못해 이번 회차는 건너뜁니다.")
        (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    video = make_video(script, character, out_dir / "video.mp4", args.provider, ROOT / "character" / f"{args.character}.png")
    meta["video"] = str(video.relative_to(ROOT))

    if args.publish in ("youtube", "both"):
        from pipeline import upload_youtube
        meta["uploads"]["youtube"] = upload_youtube.upload(video, script, args.youtube_privacy)
    if args.publish in ("instagram", "both"):
        if not args.video_url:
            raise SystemExit("인스타그램 업로드에는 --video-url (공개 URL) 이 필요합니다.")
        from pipeline import upload_instagram
        meta["uploads"]["instagram"] = upload_instagram.upload(args.video_url, script)

    if args.publish != "none":  # 올린 것만 기록해서 다음 회차가 소재를 피하게 함
        history.add({"title": script["title"], "uploads": meta["uploads"]})

    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
