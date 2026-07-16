# python

GitHub OAuth 로그인 → GitHub 리파지토리 리스트/상세 조회 → 커밋 내역 확인 → GitHub Webhook 기반 실시간 알림까지 지원하는 파이썬 프로젝트입니다.
웹 페이지(Flask)와 CLI 스크립트 두 가지 방식으로 로그인/리스트 조회를 사용할 수 있습니다.

## 구조
- `src/auth` — GitHub OAuth Authorization Code Flow 로그인 (공용 로직 + CLI용 로컬 콜백 서버)
- `src/github` — GitHub API 리파지토리 목록/검색/상세/커밋 조회 (`list_repos`, `search_repos`, `view_repo`, `list_commits`)
- `src/webapp.py` — 로그인, 리파지토리 목록/상세/커밋, GitHub Webhook 수신, SSE 실시간 스트림 (Flask)
- `src/main.py` — CLI로 로그인 후 리파지토리 목록을 터미널에 출력

## 기능
- **로그인**: GitHub OAuth Authorization Code Flow
- **리파지토리 목록** (`/repos`): 이름/설명 검색(`q`), 정렬(`sort=full_name|created|updated`, GitHub Search API로 검색 시에는 클라이언트에서 정렬)
- **리파지토리 상세** (`/repos/<owner>/<repo>`): 생성/업데이트/Push 일시(KST 변환 표시), 커밋 내역 토글 조회
- **실시간 알림**: GitHub Webhook을 받아 Server-Sent Events(SSE)로 브라우저에 즉시 반영
  - 어느 페이지에 있든 우측 하단에 토스트로 이벤트 표시
  - `/repos` 목록을 보고 있는 도중 어떤 저장소든 push가 들어오면(정렬이 "업데이트순"일 때) 해당 저장소가 바로 맨 위로 이동하며 하이라이트됨
  - `/repos/<owner>/<repo>` 상세 페이지를 보고 있는 도중 같은 저장소에 push가 들어오면 커밋 내역이 자동으로 새로고침됨

## 시작하기
1. GitHub에서 OAuth App을 등록하고(Settings > Developer settings > OAuth Apps) Client ID/Secret과 콜백 URL(`http://localhost:8080/callback`)을 등록합니다.
2. `.env.example`을 `.env`로 복사하고 `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `FLASK_SECRET_KEY`를 채웁니다. (Webhook 실시간 알림을 쓰려면 `GITHUB_WEBHOOK_SECRET`도 채우세요 — 아래 [실시간 알림 설정](#실시간-알림-github-webhook--ngrok) 참고)
3. 의존성 설치: `pip install -r requirements.txt`

### 웹 페이지로 실행
```
python3 -m flask --app src.webapp --debug run --host=0.0.0.0 --port 8080
```
`--host=0.0.0.0`을 빼면 `127.0.0.1`에만 열려서 브라우저에서 `localhost`로 접속 시 (IPv6 우선 탐색 때문에) 연결이 거부될 수 있습니다.

`http://localhost:8080` 접속 → 로그인 페이지에서 "GitHub로 로그인" 클릭 → GitHub 로그인/동의 후 리파지토리 목록 페이지로 이동합니다.

### CLI로 실행
```
python -m src.main
```
브라우저가 열리고 GitHub 로그인/동의 화면으로 이동합니다. 로그인을 완료하면 로컬 콜백 서버가 인가 코드를 받아 토큰으로 교환하고, 리파지토리 목록이 터미널에 출력됩니다.

웹/CLI 둘 다 쓰려면 콜백 URL이 서로 다르므로(`8080` 포트 공용), 한 번에 하나씩만 실행하거나 GitHub OAuth 앱에 콜백 URL을 추가로 등록하세요.

## 실시간 알림 (GitHub Webhook + ngrok)

push 같은 GitHub 이벤트를 실시간으로 받아 화면에 반영하려면, GitHub이 내 로컬 서버(`localhost:8080`)로 webhook을 보낼 수 있어야 합니다. 로컬 서버는 인터넷에서 직접 접근할 수 없으므로, [ngrok](https://ngrok.com/)으로 임시 공개 URL을 만들어 터널링합니다.

### 1. ngrok 설치 및 실행
```
brew install ngrok   # 최초 1회 (Mac 기준, 다른 OS는 ngrok 공식 문서 참고)
ngrok config add-authtoken <ngrok 계정의 authtoken>   # 최초 1회, ngrok.com에서 발급
```

Flask 서버(`8080` 포트)를 먼저 띄운 상태에서, **같은 8080 포트**로 ngrok을 실행합니다.
```
ngrok http --url=maximum-staple-panhandle.ngrok-free.dev 8080
```
maximum-staple-panhandle.ngrok-free.dev는 발급된 임시 공개 URL을 넣으면 된다.

실행하면 터미널에 아래와 같은 공개 URL이 나옵니다 (매번 랜덤하게 바뀝니다. 고정 도메인은 유료 플랜에서 `ngrok http --url=<예약한 도메인> 8080`으로 사용 가능).
```
Forwarding    https://xxxx-xxxx-xxxx.ngrok-free.dev -> http://localhost:8080
```
`http://127.0.0.1:4040`에 접속하면 ngrok을 거쳐간 모든 요청/응답을 실시간으로 확인할 수 있어(webhook이 잘 도착하는지, 상태 코드가 뭔지) 디버깅에 유용합니다.

### 2. `.env`에 Webhook Secret 설정
```
GITHUB_WEBHOOK_SECRET=아무-랜덤-문자열
```
설정해두면 `/github/webhook`이 GitHub이 보낸 요청인지 HMAC-SHA256 서명(`X-Hub-Signature-256`)으로 검증합니다. 비워두면 로컬 테스트 편의상 검증을 건너뛰지만, 외부에 노출되는 상태이므로 반드시 채워서 쓰는 걸 권장합니다.

### 3. GitHub 저장소에 Webhook 등록
대상 저장소 → **Settings → Webhooks → Add webhook**
- **Payload URL**: `https://xxxx-xxxx-xxxx.ngrok-free.dev/github/webhook` (ngrok이 준 URL + `/github/webhook`)
- **Content type**: `application/json` (기본값인 `application/x-www-form-urlencoded`로 둬도 서버가 두 형식 다 처리하지만, `application/json`을 권장)
- **Secret**: 위 `GITHUB_WEBHOOK_SECRET`과 동일한 값
- **Which events**: 최소 `Just the push event` 체크

저장하면 GitHub이 바로 테스트 ping을 보내고, **Recent Deliveries** 탭에서 응답 코드(200이면 정상)를 확인할 수 있습니다.

### 4. 확인
Flask 서버를 실행한 채로 브라우저에서 로그인 후 `/repos`나 `/repos/<owner>/<repo>` 페이지를 열어두고, 등록한 저장소에 `git push`를 해보세요. 우측 하단에 토스트가 뜨고, 목록/커밋 내역이 실시간으로 갱신됩니다.

> ngrok 무료 플랜은 URL이 재시작할 때마다 바뀌므로, 재시작했다면 GitHub 저장소의 Webhook Payload URL도 새 주소로 업데이트해야 합니다.

## 테스트
```
pytest
```
