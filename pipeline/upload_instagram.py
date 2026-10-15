"""Instagram Reels 업로드 (Instagram Graph API).

필요한 환경변수: IG_USER_ID, IG_ACCESS_TOKEN
- 인스타그램 프로페셔널(비즈니스/크리에이터) 계정 + Meta 개발자 앱 + instagram_content_publish 권한
- 영상은 인터넷에서 접근 가능한 공개 URL 이어야 합니다(Graph API 가 직접 내려받음).
"""
import os
import time

import requests

GRAPH = "https://graph.facebook.com/v23.0"


def upload(video_url: str, script: dict) -> str:
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    caption = script["description"] + "\n\n" + " ".join(script["hashtags"])

    r = requests.post(
        f"{GRAPH}/{user_id}/media",
        data={"media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": token},
        timeout=60,
    )
    r.raise_for_status()
    container_id = r.json()["id"]

    for _ in range(60):
        status = requests.get(
            f"{GRAPH}/{container_id}", params={"fields": "status_code", "access_token": token}, timeout=30
        ).json()
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"인스타그램 영상 처리 실패: {status}")
        time.sleep(10)
    else:
        raise TimeoutError("인스타그램 영상 처리 대기 시간 초과")

    r = requests.post(
        f"{GRAPH}/{user_id}/media_publish", data={"creation_id": container_id, "access_token": token}, timeout=60
    )
    r.raise_for_status()
    return r.json()["id"]
