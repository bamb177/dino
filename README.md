# 노후룡 쭈구리 밈 쇼츠 자동화

직장인 아기 공룡 **노후룡 쭈구리**가 나오는 9~12초 세로 밈 영상을 **주 3회(월/수/금 18:00 KST)** 자동으로 만들고, 유튜브 쇼츠에 올리는 파이프라인입니다.

```
트렌드 수집 → 매니저 Claude가 소재 선정 → 대본 작성 → 매니저 Claude가 검수(반려 시 최대 3번 재작성)
            → 영상 생성(local 또는 Veo) → 승인된 경우에만 YouTube 업로드 → 업로드 기록 저장
```

기본값은 **아무것도 업로드하지 않는** 상태입니다. 아래 "켜는 순서"를 따라 직접 켜야 올라갑니다.

## 켜는 순서

1. **PR 머지**: 스케줄(cron)은 기본 브랜치에 머지된 뒤부터 돌기 시작합니다.
2. **시크릿 등록** (Settings → Secrets and variables → Actions → Secrets)

   | 이름 | 용도 | 필수 |
   | --- | --- | --- |
   | `ANTHROPIC_API_KEY` | 매니저 Claude (소재 선정, 대본, 검수) | 필수 |
   | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | 유튜브 업로드 | 업로드할 때 |
   | `YT_API_KEY` | 유튜브 인기 급상승 목록을 트렌드에 추가 | 선택 |
   | `GEMINI_API_KEY` | Veo 영상 생성 | `veo` 쓸 때 |

3. **수동 실행으로 먼저 확인**: Actions → Make meme short → Run workflow (모두 기본값). 끝나면 Artifacts 의 mp4 와 `meta.json` 확인.
4. **업로드 켜기** (Variables 탭): `AUTO_PUBLISH=true`. 공개 범위 `YT_PRIVACY` 는 기본 `private` 이라, 몇 편은 비공개로 올려서 확인한 뒤 `public` 으로 바꾸세요.
5. **영상 AI 켜기** (선택): `VIDEO_PROVIDER=veo` (아래 비용 참고).

멈추고 싶으면 `AUTO_PUBLISH` 를 지우거나 false 로 바꾸면 됩니다.

## 계정/키를 얻는 방법

- **Anthropic**: console.anthropic.com 에서 API 키 발급(유료 결제 필요).
- **YouTube 업로드**: Google Cloud 콘솔에서 프로젝트 생성 → YouTube Data API v3 사용 설정 → OAuth 클라이언트(데스크톱 앱) 생성 → `https://www.googleapis.com/auth/youtube.upload` 범위로 동의하고 받은 refresh token 을 `YT_REFRESH_TOKEN` 에 저장. 채널 소유 계정으로 로그인해야 합니다.
  - 구글 감사(audit)를 통과하지 않은 API 프로젝트로 올린 영상은 **비공개로 잠깁니다.** 그 사이에는 비공개로 올리고 유튜브 스튜디오에서 직접 공개로 바꾸는 방식이 현실적입니다.
- **Gemini(Veo)**: aistudio.google.com 에서 API 키 발급, 결제 설정 필요.

## 영상 만드는 방식

| 방식 | 비용 | 품질 |
| --- | --- | --- |
| `local` (기본) | 무료 | 코드로 그린 단순한 캐릭터 + 자막. 채널 초반 테스트용 |
| `veo` (추천) | 아래 참고 | AI 가 만든 8초 영상(귀여운 3D 풍) 위에 한글 자막. 캐릭터 PNG(`character/dino.png`)를 넣으면 참조 이미지로 써서 외형을 맞춥니다 |

**Veo 비용 (제가 기억하는 대략치라, 쓰기 전에 Google AI 가격 페이지에서 꼭 확인하세요)**: Veo 3.1 Fast 는 초당 대략 $0.15, 표준 모델은 초당 대략 $0.40 안팎입니다. 8초 영상 한 편이 약 $1.2(Fast) ~ $3.2(표준), 주 3회면 한 달 13편 안팎이라 **월 $16 ~ $42 정도**를 예상하면 됩니다. 매니저 Claude 호출은 한 편에 수백 원 수준으로 추정합니다. 생성이 안전 필터에 걸리거나 실패해도 요금이 나갈 수 있습니다.

Veo 연결 코드는 SDK 의 타입 이름까지만 확인했고 **실제 API 호출은 아직 해 보지 못했습니다.** 키를 넣고 수동 실행으로 먼저 한 편 확인해 주세요.

## 매니저 Claude 가 하는 일

- `pipeline/trends.py`: Google 트렌드 급상승 RSS(+ `YT_API_KEY` 가 있으면 유튜브 인기 영상 제목)에서 요즘 키워드 수집. 네트워크가 막히면 캐릭터 테마로 대체.
- `pipeline/manager.py`: 재난·정치·실존 인물 키워드를 피해 소재를 고르고, 대본이 아래 기준을 통과해야 영상으로 만듭니다. 3번 반려되면 그 회차는 건너뜁니다.
  오리지널 여부, 안전·광고 친화, 저작권(유행 음악 금지), 훅과 반전, 형식, 최근 영상과 중복 여부
- `data/history.json`: 올린 영상 기록. 워크플로우가 업로드 후 자동 커밋하며, 다음 회차가 같은 소재를 피하는 데 씁니다. (main 브랜치에 보호 규칙이 있으면 이 커밋이 막힐 수 있어요.)

## 수익화 체크리스트

- **YouTube 파트너 프로그램**: 광고 수익은 구독자 1,000명 + (최근 12개월 시청 4,000시간 또는 최근 90일 쇼츠 조회 1,000만). 초기 단계(팬 후원 등)는 구독자 500명 + 최근 90일 공개 영상 3개 + (시청 3,000시간 또는 쇼츠 조회 300만). 수치는 기억에 의존한 것이라 YouTube 도움말에서 확인하세요.
- **자동화의 가장 큰 위험은 "반복·대량생산 콘텐츠" 판정**입니다. 똑같은 틀을 찍어내면 수익화가 거절될 수 있어서, 매니저가 매번 새 상황을 쓰도록 했지만 처음 몇 주는 직접 영상을 보고 다듬으세요.
- **AI 표기**: 업로드 시 `containsSyntheticMedia` 가 켜지고, 영상 우하단에 "AI 생성 콘텐츠" 문구가 들어갑니다.
- 유행 음악·남의 영상은 쓰지 않습니다. 저작권 신고가 쌓이면 채널에 불이익이 옵니다.
- 인스타 릴스 업로드(`--publish instagram --video-url <URL>`)는 코드만 있고 자동화 워크플로우에는 넣지 않았습니다. 인스타는 파일 대신 공개 URL 이 필요합니다.

## 로컬 실행

```bash
pip install -r requirements.txt   # ffmpeg 와 한글 폰트(fonts-noto-cjk)도 필요
python run.py                     # 영상만 생성 (out/<시각>/)
python run.py --topic "점심 메뉴 고르기"
python run.py --provider veo --publish youtube --youtube-privacy private
```

## 캐릭터 바꾸기

`character/dino.yaml` 의 이름, 성격, 말투, 테마를 고치면 대본에 바로 반영됩니다. 외형은 `character/dino.png`(투명 배경 PNG)를 넣으면 `local` 방식에서도 그 그림을 씁니다.
