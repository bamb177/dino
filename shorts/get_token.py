"""YouTube 업로드 권한(리프레시 토큰)을 한 번 발급받는 스크립트. 내 컴퓨터에서 실행하세요.

사용법:
  pip install google-auth-oauthlib
  python -m shorts.get_token client_secret.json
브라우저가 열리면 업로드할 유튜브 채널의 구글 계정으로 로그인 → 허용.
출력되는 3개 값을 GitHub Secrets에 넣으면 끝입니다.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
    flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    info = json.load(open(path))
    info = info.get("installed") or info.get("web")
    print("\n아래 3개를 GitHub 저장소 Settings → Secrets and variables → Actions 에 추가하세요.\n")
    print(f"YT_CLIENT_ID      = {info['client_id']}")
    print(f"YT_CLIENT_SECRET  = {info['client_secret']}")
    print(f"YT_REFRESH_TOKEN  = {creds.refresh_token}")


if __name__ == "__main__":
    main()
