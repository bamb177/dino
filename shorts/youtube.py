"""YouTube Data API 업로드.

필요한 환경변수 (GitHub Secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
리프레시 토큰은 `python -m shorts.get_token` 으로 한 번만 발급받으면 됩니다.
"""
from __future__ import annotations

import datetime as dt
import os
from zoneinfo import ZoneInfo

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
KST = ZoneInfo("Asia/Seoul")


def _service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def next_slot(hour: int, now: dt.datetime | None = None) -> dt.datetime:
    """다음 게시 시각(한국 시간 hour시). 이미 지났으면 다음 날."""
    now = now or dt.datetime.now(KST)
    slot = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if slot <= now + dt.timedelta(minutes=20):
        slot += dt.timedelta(days=1)
    return slot


def upload(video: str, meta: dict) -> str:
    from googleapiclient.http import MediaFileUpload

    privacy = os.environ.get("YT_PRIVACY", "scheduled")  # scheduled | public | private | unlisted
    status = {
        "selfDeclaredMadeForKids": os.environ.get("YT_MADE_FOR_KIDS", "false").lower() == "true",
        "embeddable": True,
    }
    if privacy == "scheduled":
        at = next_slot(int(os.environ.get("PUBLISH_HOUR_KST", "18")))
        status["privacyStatus"] = "private"
        status["publishAt"] = at.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        status["privacyStatus"] = privacy
    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": meta["description"][:4900],
            "tags": meta.get("tags", [])[:15],
            "categoryId": "1",  # Film & Animation
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": status,
    }
    req = _service().videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(video, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True),
    )
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    when = status.get("publishAt", status["privacyStatus"])
    print(f"업로드 완료: https://youtube.com/shorts/{vid} ({when})")
    return vid
