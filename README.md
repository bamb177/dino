# 디노 밈 파이프라인

직장인 아기 공룡 **디노**가 나오는 9~12초 세로 밈 영상(YouTube Shorts / Instagram Reels)을 만드는 파이프라인입니다.

```
대본(Claude) → 장면 렌더링(Pillow) → mp4 인코딩(ffmpeg) → [선택] 업로드(YouTube / Instagram)
```

업로드는 `--publish` 를 직접 지정할 때만 일어나고, 유튜브는 기본값이 **비공개(private)** 입니다.

## 바로 해보기 (GitHub Actions)

1. 저장소 → **Actions → Make meme video → Run workflow**
2. `publish` 는 `none` 그대로 두고 실행
3. 끝나면 실행 화면 아래 **Artifacts → meme-video** 에서 mp4 를 내려받아 확인

`ANTHROPIC_API_KEY` 시크릿이 없으면 내장 예시 대본 2개 중 하나로 만들어집니다.

## 로컬 실행

```bash
pip install -r requirements.txt   # ffmpeg 와 한글 폰트(fonts-noto-cjk)도 필요
python run.py --topic "점심 메뉴 고르기"
```

결과는 `out/<시각>/video.mp4`, `meta.json` 에 저장됩니다.

## 캐릭터 바꾸기

- 성격/말투/테마: `character/dino.yaml`
- 외형: `character/dino.png` (투명 배경 PNG)를 넣으면 코드로 그린 기본 공룡 대신 그 그림을 씁니다.
  AI 이미지 생성 도구로 만든 캐릭터 시트나, 직접 그린 그림을 넣으면 됩니다.

## 시크릿 (Settings → Secrets and variables → Actions)

| 이름 | 용도 | 얻는 곳 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | 매번 새 대본 생성 | console.anthropic.com |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET` | 유튜브 업로드 | Google Cloud 콘솔 → YouTube Data API v3 사용 설정 → OAuth 클라이언트(데스크톱 앱) |
| `YT_REFRESH_TOKEN` | 유튜브 업로드 | 위 OAuth 클라이언트로 `youtube.upload` 범위 동의 후 받은 refresh token |
| `IG_USER_ID`, `IG_ACCESS_TOKEN` | 인스타 릴스 업로드 | 인스타 프로페셔널 계정 + 연결된 페이스북 페이지 + Meta 개발자 앱(`instagram_content_publish`) |

주의할 점
- Google 의 **감사(audit)를 통과하지 않은 API 프로젝트로 올린 영상은 비공개로 잠깁니다.** 감사 전에는 비공개로 올린 뒤 유튜브 스튜디오에서 직접 공개로 바꾸는 방식이 현실적입니다.
- 인스타 Graph API 는 영상 파일이 아니라 **공개 URL** 을 받습니다. 그래서 워크플로우에는 아직 인스타 업로드를 넣지 않았고, `python run.py --publish instagram --video-url <URL>` 로만 동작합니다.

## 수익화 체크리스트

- **YouTube 파트너 프로그램(YPP)**
  - 광고 수익: 구독자 1,000명 + (최근 12개월 시청 4,000시간 **또는** 최근 90일 쇼츠 조회수 1,000만)
  - 팬 후원 등 초기 단계(한국 지원): 구독자 500명 + 최근 90일 공개 영상 3개 + (시청 3,000시간 또는 쇼츠 조회수 300만)
  - **같은 틀을 찍어내는 반복·대량생산 콘텐츠는 수익화가 거절됩니다.** 대본이 매번 새로운 상황을 쓰도록 했지만, 사람이 고르고 다듬는 단계는 꼭 남겨 두세요.
- **AI 표기**: 업로드 시 YouTube `containsSyntheticMedia`(변경·합성 콘텐츠) 표시를 켜 두었고, 영상 우하단에 "AI 생성 콘텐츠" 문구가 들어갑니다. 인스타는 업로드 후 'AI 정보' 라벨을 확인하세요.
- **Instagram**: 릴스 자체 광고 수익은 제한적이라 팔로워를 모은 뒤 브랜드 협찬, 구독, 선물 기능이 주 수익원입니다.
