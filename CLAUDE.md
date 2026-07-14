# python_cicd

## 프로젝트 개요
GitHub OAuth 로그인, GitHub 리파지토리 리스트 조회, CI/CD 파이프라인 구축을 목표로 하는 파이썬 프로젝트

## 에이전트 구성
이 프로젝트는 멀티 에이전트로 운영됩니다.

| 에이전트 | 역할 | 담당 범위 |
|---------|------|---------|
| project-lead | 리더 - 플랜 수립 및 조율 | 전체 |
| auth | GitHub OAuth 로그인/인증 플로우 구현 | src/auth |
| github-api | GitHub API 리파지토리 리스트 조회 구현 | src/github |
| cicd | GitHub Actions 기반 CI/CD 파이프라인 구축 | .github/workflows |

## 작업 방식
1. 사용자는 `project-lead` 에이전트에게 명령한다
2. `project-lead`가 플랜을 수립하고 하위 에이전트에게 분배한다
3. 각 에이전트는 작업 전 `.claude/memory/`를 먼저 확인한다
4. 완료 후 `project-lead`가 결과를 취합하여 보고한다

## 메모리 공간
`.claude/memory/` — 에이전트 간 분석 이력 공유 공간

## 주요 규칙
- 모든 응답은 한국어로 한다
- 각 에이전트는 담당 범위 외 파일을 수정하지 않는다
- 새로운 분석 내용은 반드시 메모리 공간에 저장한다
- OAuth 클라이언트 시크릿 등 민감 정보는 코드/워크플로우에 하드코딩하지 않고 환경변수 또는 GitHub Actions Secrets로 관리한다
