"""YouTube Shorts 업로드 (YouTube Data API v3).

필요한 환경변수: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
- Google Cloud 프로젝트에서 YouTube Data API v3 활성화 + OAuth 클라이언트 생성
- 감사(audit)를 통과하지 않은 앱으로 올린 영상은 '비공개'로 고정되므로 기본값도 private 입니다.
"""
import os
from pathlib import Path


def upload(video: Path, script: dict, privacy: str = "private") -> str:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": f"{script['title']} #shorts"[:100],
            "description": script["description"] + "\n\n" + " ".join(script["hashtags"]),
            "tags": [h.lstrip("#") for h in script["hashtags"]],
            "categoryId": "23",  # Comedy
            "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        },
    }
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=MediaFileUpload(str(video), resumable=True)
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return f"https://youtube.com/shorts/{response['id']}"
