# 귀여운 캐릭터 쇼츠 자동화

매일 아침 AI가 오리지널 캐릭터(디노·모찌·냥구·부부) 쇼츠를 1편 만들고, 가람님이 휴대폰으로 1분 검수한 뒤 `approved` 라벨을 붙이면 유튜브에 예약 업로드되는 파이프라인이에요.

```
매일 08:00 (GitHub Actions)
  트렌드·계절 확인 → Claude가 대본 작성 → 음성(edge-tts) + 배경음악(직접 합성)
  → 캐릭터 애니메이션 렌더 (1080x1920, 25~40초)
  → GitHub Release에 영상 업로드 + "[검수]" 이슈 생성
가람님: 이슈에서 영상 보고 라벨 붙이기
  approved → 유튜브에 예약 업로드 (기본: 그날/다음날 18:00 공개)
  rejected → 영상 삭제
```

## 비용 (월 30편 기준)

| 항목 | 도구 | 월 비용 |
|---|---|---|
| 대본 | Claude API (`claude-opus-5-5`, effort low) | 약 $1~2 (편당 3~5센트) |
| 음성 | edge-tts (마이크로소프트 무료 음성) | 무료 |
| 그림·애니메이션·음악 | 코드로 직접 그림/합성 | 무료 |
| 실행 서버 | GitHub Actions (편당 약 3분) | 무료 한도 안 |
| 업로드 | YouTube Data API | 무료 |
| **합계** | | **약 2천~3천 원** |

## 저작권과 수익 창출 정책

- 캐릭터, 배경, 음악을 모두 코드로 새로 만들어요. 남의 밈 이미지나 영상, 노래는 쓰지 않아요.
- 트렌드는 주제 아이디어로만 써요. 실존 인물, 브랜드, 다른 작품의 캐릭터나 대사는 쓰지 말라고 대본 AI에게 지시해 뒀어요.
- 유튜브의 "반복적·대량 생산 콘텐츠" 기준에 걸리지 않도록, 매번 형식(상황극·공감·퀴즈·일기·상식·도전)과 캐릭터 조합, 배경, 음악을 바꿔요. 최근 기록은 `state/history.json`에 남겨서 같은 조합이 연달아 나오지 않게 해요.
- 그래도 검수할 때 "어제랑 너무 비슷한데?" 싶으면 `rejected`를 붙여 주세요. 사람이 고르는 과정이 채널 품질을 지켜줘요.

---

## 처음 한 번만 하는 설정 (약 30분)

### 1. 유튜브 채널 만들기
1. 채널용 구글 계정으로 [youtube.com](https://youtube.com)에 로그인한 뒤 프로필 → **채널 만들기**를 눌러요.
2. [YouTube Studio](https://studio.youtube.com) → 설정 → 채널 → **기능 사용 자격요건**에서 휴대폰 인증을 해요. 이걸 해야 15분 넘는 영상이나 맞춤 썸네일 같은 기능이 열려요.

### 2. Claude API 키
1. [console.anthropic.com](https://console.anthropic.com)에서 결제수단을 등록하고 5달러 정도 충전해요. 몇 달은 충분해요.
2. **API Keys** → Create Key로 키를 만들고 복사해요.

### 3. YouTube 업로드 권한(OAuth) 만들기
1. [Google Cloud Console](https://console.cloud.google.com)에서 새 프로젝트를 만들어요. 이름은 예를 들어 `dino-shorts`로 하면 돼요.
2. **API 및 서비스 → 라이브러리**에서 **YouTube Data API v3**를 찾아 **사용**을 눌러요.
3. **OAuth 동의 화면**(Google Auth Platform)에서 외부 사용자로 설정하고, 앱 이름과 이메일을 넣어요. **대상(Audience)에서 게시 상태를 "프로덕션(In production)"으로 바꿔요.**
   - 테스트 상태로 두면 7일마다 권한이 만료돼서 업로드가 멈춰요.
   - 확인되지 않은 앱이라는 경고가 떠도 본인만 쓰는 거라 괜찮아요.
4. **사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID → 데스크톱 앱**으로 만든 뒤 JSON을 다운로드해서 `client_secret.json`으로 저장해요.
5. 내 컴퓨터에서 아래 명령을 실행해요.
   ```bash
   pip install google-auth-oauthlib
   python -m shorts.get_token client_secret.json
   ```
   브라우저가 열리면 **채널을 만든 구글 계정**으로 로그인하고 허용을 눌러요. `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` 세 값이 출력돼요.

### 4. GitHub에 비밀값 넣기
저장소 **Settings → Secrets and variables → Actions → New repository secret**에서 아래 4개를 추가해요.

| 이름 | 값 |
|---|---|
| `ANTHROPIC_API_KEY` | 2단계에서 만든 키 |
| `YT_CLIENT_ID` | 3단계 출력값 |
| `YT_CLIENT_SECRET` | 3단계 출력값 |
| `YT_REFRESH_TOKEN` | 3단계 출력값 |

### 5. 첫 실행
**Actions → "Shorts - 매일 영상 만들기" → Run workflow**를 누르면 3~5분 뒤 **Issues**에 `[검수]` 이슈가 생겨요. 그다음부터는 매일 오전 8시에 자동으로 만들어져요.

> ⚠️ **꼭 알아두세요: 유튜브 API 심사**
> Google Cloud에서 새로 만든 API 프로젝트로 올린 영상은, 유튜브의 [API 준수 심사(Audit)](https://support.google.com/youtube/contact/yt_api_form)를 통과하기 전까지 **비공개로 잠겨요.** 무료이고, 신청서에 "본인 채널에 직접 만든 애니메이션을 올리는 용도"라고 쓰면 돼요. 보통 1~4주 걸려요.
> 심사를 기다리는 동안에는 검수 이슈의 Release 링크에서 mp4를 받아 유튜브 앱으로 직접 올리시면 돼요(1분이면 돼요).

---

## 매일 하는 일 (1분)
1. GitHub 앱 알림으로 `[검수]` 이슈가 와요.
2. Release 링크에서 영상을 보고 대본을 훑어봐요.
3. 괜찮으면 Labels에서 `approved`를 붙여요. 별로면 `rejected`를 붙여요.

## 설정 바꾸기 (선택)
**Settings → Secrets and variables → Actions → Variables** 탭에서 바꿀 수 있어요.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `YT_PRIVACY` | `scheduled` | `scheduled`(예약 공개) / `public`(바로 공개) / `private` / `unlisted` |
| `PUBLISH_HOUR_KST` | `18` | 예약 공개 시각(한국 시간) |

만드는 시각을 바꾸려면 `.github/workflows/shorts-daily.yml`의 `cron`을 고치면 돼요(UTC 기준이라 한국 시간에서 9시간을 빼요).

**아동용 설정:** 기본값은 "아동용 아님"이에요. 귀여운 캐릭터라도 아이들만을 겨냥한 내용이 아니면 아동용이 아니에요. 아동용으로 표시하면 댓글이 막히고 광고 수익이 크게 줄어요. 정말 아동 대상이라면 `YT_MADE_FOR_KIDS=true`로 바꿔야 하고, 이건 법적 의무라서 실제 내용에 맞게 정해 주세요.

## 내 컴퓨터에서 테스트
```bash
# ffmpeg, 한글 폰트(Noto Sans CJK), Python 3.10+ 필요
pip install -r shorts/requirements.txt
python -m shorts make --offline           # API 키 없이 샘플 대본으로
ANTHROPIC_API_KEY=... python -m shorts make  # 실제 AI 대본으로
python -m shorts.characters               # 캐릭터 표정 시트 이미지 저장
```

## 파일 구성
| 파일 | 하는 일 |
|---|---|
| `characters.py` | 캐릭터 4종 디자인과 표정 8가지 |
| `writer.py` | 트렌드·계절 수집, 형식/캐릭터/배경 고르기, Claude 대본 작성 |
| `audio.py` | 캐릭터별 음성, 배경음악 합성, 믹싱 |
| `render.py` | 배경 8종, 효과, 자막, 애니메이션 렌더 |
| `youtube.py` | 유튜브 업로드와 예약 |
| `get_token.py` | 업로드 권한 발급(한 번만) |
