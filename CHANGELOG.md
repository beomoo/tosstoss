# Changelog

## Unreleased — Phase 2 CP2-A — 2026-08-23

### Added

- 실제 transport 없이 `services/api/src/toss_dashboard_api/connectors/toss` 전용 namespace scaffold
- optional server-only `TOSS_CLIENT_ID`, `TOSS_CLIENT_SECRET` secret-aware 설정과 빈 `.env.example` 항목
- exact Toss origin·12개 callable endpoint/rate metadata·connector 경로 정책 데이터
- HTTP import, frontend direct Toss, 계좌·주문 endpoint, account header, generic connector와 공개 credential 환경변수 negative canary

### Changed

- `httpx==0.28.1`을 exact runtime dependency로 승격하고 source/runtime 위치·version·lock hash 검증을 강화
- backend test inventory를 172개에서 176개로 확대
- CP2의 범위를 바꾸지 않고 CP2-A부터 CP2-D까지의 실행 순서를 계획에 명시

### Security

- `httpx` import 허용 가능 위치를 Toss backend connector namespace 하나로 제한
- `Authorization`, Bearer, client ID/secret, access token, cookie, set-cookie redaction 보강
- Toss/client secret assignment와 Authorization Bearer 합성 카나리를 secret scan에서 거부
- `.env`, `.env.local`, `.env.*.local`과 동등한 ignore 규칙을 검증하고 실제 credential·`.env` 파일을 추가하지 않음
- 계좌·보유·주문·구매가능금액·매도가능수량·수수료·조건주문 surface와 `X-Tossinvest-Account`를 runtime에서 계속 금지

### QA

- provider contract drift `NO`: REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- Node.js 24.19.0, npm 11.17.0에서 통합 `scripts/test.ps1` exit code 0
- backend 176/176, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI drift, build 2회, secret scan, policy scan PASS
- validated implementation commit: `e1bca561998d745bb357dc8c92f835926886e770`

### Limitations

- CP2-A는 CP2 전체 완료가 아니다. OAuth/token manager, HTTP request, rate limit/retry, live preflight는 CP2-B 이후 범위이며 시작하지 않았다.
- `requirements.in`과 `requirements.lock`은 baseline부터 `httpx==0.28.1`과 승인 hash를 포함해 파일 내용 변경이 필요하지 않았다.

## 0.1.0 — 2026-08-22

### Added

- FastAPI/Pydantic 기반 Phase 1 로컬 fixture API와 안전한 오류 envelope
- SQLite metadata migration, 읽기 전용 fixture repository와 멱등 import audit
- 합성 KR/US issuer·security, 가격·수급·재무·기관 보유·공시 diff·가치평가·데이터 품질·analysis packet fixture
- Next.js/TypeScript Company 및 Data Quality 읽기 전용 화면과 loading/empty/error/not-found 상태
- OpenAPI snapshot과 `openapi-typescript` 생성 타입 drift 검사
- Windows PowerShell setup/dev/build/test/migrate/import/E2E/secret/policy 스크립트
- localhost·외부 네트워크·프로세스 소유권·브라우저 transport·테스트 inventory fail-closed gate
- Phase 1 샘플 API JSON, 실행 로그와 Playwright 화면 증거

### Changed

- ADR-005부터 ADR-008까지 Phase 1 계약·식별자·저장 경계·로컬 fail-closed 결정을 `ACCEPTED`로 기록
- Windows Node.js 지원 하한을 24.16.0으로 올리고 `.node-version`을 24.19.0으로 고정하는 ADR-009를 `PROPOSED`로 추가
- 모든 주요 PowerShell 진입점이 정확한 Node/npm 실행 파일과 상속 `NODE_OPTIONS`를 작업 전에 검증하도록 강화
- 최종 테스트 inventory를 backend 172개, frontend 43개, E2E 2개로 확대·고정
- 프로젝트 상태를 Phase 1 완료·독립 QA PASS로 갱신

### Fixed

- Node.js 24.15.0의 Windows TCP 네이티브 충돌을 지원 버전 사전검사로 회피
- E2E frontend 기동을 검증된 정확한 `npm.cmd` 경로로 고정
- Node engine 변경 뒤 이전 값에 남아 있던 비밀정보 스캐너의 `package-lock.json` 승인 digest를 현재 추적 잠금 파일과 동기화

### Security

- FastAPI와 Next.js를 127.0.0.1 전용으로 제한하고 정확한 host/CORS allowlist 적용
- 실제 키·계좌·주문·OpenAI·외부 데이터 connector를 구현하지 않음
- source, 브라우저 bundle, QA artifact와 로그를 비밀정보 검사 범위에 포함
- destructive migration downgrade를 명시적 disposable DB 경로와 확인 플래그로 제한
- Python/Node의 non-loopback 연결과 브라우저의 비허용 요청을 테스트에서 차단·수집

### QA

- 구현 기준 commit: `f358fa3f0d1af44d0348bc5ba5c48be7866d7b21`
- 최종 독립 검증 commit: `57b2a63ead06d03191d8094e1689b8d2ab3d7764`
- PR #1을 merge commit `b1829a7375704271a21267e1fcf62808147be593`으로 `main`에 병합
- Phase 1 release baseline annotated tag: `v0.1.0`
- Node.js 24.19.0, npm 11.17.0에서 setup 2회와 개발 서버 smoke 통과
- backend pytest 172개, frontend Vitest 43개(10 files), Playwright 2개 통과
- Ruff/ESLint, mypy 40 files, TypeScript, process cleanup canary 20회 통과
- migration 왕복, fixture 멱등성, OpenAPI drift, Next build, secret scan, policy scan 통과
- 최종 통합 실행은 secret scan 직전까지 기존 로그를 회수하고, stale lock digest 수정 후 실패한 보안·정책 게이트만 별도로 재검증해 중복 실행을 피함

### Limitations

- 모든 회사·시장·공시·기관 데이터는 합성 fixture이며 실제 투자 데이터가 아님
- 실제 Toss/OpenDART/SEC/news/macro 연결, 계좌, 주문, 자동매매, OpenAI API는 비범위
- ADR-009는 계속 `PROPOSED`이며, Phase 2 전용 상세 실행계획은 아직 작성되지 않음

## 0.1.0-docs — 2026-08-16

### Added

- 전체 단계별 구현계획
- 제품 요구사항
- 아키텍처와 데이터 계약
- SEC 13F·DART 지분공시 기반 기관 포지션 사양
- 가치평가, 공시 문장 비교, 매크로 영향 사양
- 자산제곱 후속 인터페이스
- 보안·운영 원칙
- Phase별 승인 기준
- Codex `/plan`, `/goal`, 독립 리뷰 프롬프트
- QA 템플릿

### Security

- 실제 주문 기능 비범위
- OpenAI API 비사용
- 시크릿 서버 전용
- 로컬 읽기 전용 우선
