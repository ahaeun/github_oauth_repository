# python_cicd

GitHub OAuth 로그인 → GitHub 리파지토리 리스트 조회 → CI/CD 파이프라인 구축을 목표로 하는 파이썬 프로젝트입니다.
웹 페이지(Flask)와 CLI 스크립트 두 가지 방식으로 로그인/리스트 조회를 사용할 수 있습니다.

## 구조
- `src/auth` — GitHub OAuth Authorization Code Flow 로그인 (공용 로직 + CLI용 로컬 콜백 서버)
- `src/github` — GitHub API 리파지토리 리스트 조회
- `src/webapp.py` — 로그인 페이지 / 리파지토리 목록 페이지 (Flask)
- `src/main.py` — CLI로 로그인 후 리파지토리 목록을 터미널에 출력
- `.github/workflows` — GitHub Actions CI (lint + test)

## 시작하기
1. GitHub에서 OAuth App을 등록하고(Settings > Developer settings > OAuth Apps) Client ID/Secret과 콜백 URL(`http://localhost:8080/callback`)을 등록합니다.
2. `.env.example`을 `.env`로 복사하고 `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `FLASK_SECRET_KEY`를 채웁니다.
3. 의존성 설치: `pip install -r requirements.txt`

### 웹 페이지로 실행
```
python -m flask --app src.webapp run --host=0.0.0.0 --port 8080
```
`--host=0.0.0.0`을 빼면 `127.0.0.1`에만 열려서 브라우저에서 `localhost`로 접속 시 (IPv6 우선 탐색 때문에) 연결이 거부될 수 있습니다.

`http://localhost:8080` 접속 → 로그인 페이지에서 "GitHub로 로그인" 클릭 → GitHub 로그인/동의 후 리파지토리 목록 페이지로 이동합니다.

### CLI로 실행
```
python -m src.main
```
브라우저가 열리고 GitHub 로그인/동의 화면으로 이동합니다. 로그인을 완료하면 로컬 콜백 서버가 인가 코드를 받아 토큰으로 교환하고, 리파지토리 목록이 터미널에 출력됩니다.

웹/CLI 둘 다 쓰려면 콜백 URL이 서로 다르므로(`8080` 포트 공용), 한 번에 하나씩만 실행하거나 GitHub OAuth 앱에 콜백 URL을 추가로 등록하세요.

## 테스트
```
pytest
```
