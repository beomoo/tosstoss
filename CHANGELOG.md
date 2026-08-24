# Changelog

## Unreleased — Phase 2 CP3-A Independent Review Fix — 2026-08-25

### Changed

- independent review `CHANGES REQUIRED`의 P1-01을 반영해 valid provider identity 기준 `ProviderPriceSnapshot`/latest storage와 verified-only canonical current-price view를 분리했다. nullable `security_id` linkage 때문에 Phase 2 provider-scoped 목표가 Phase 3 OpenDART/Phase 4 SEC regulatory mapping에 순환 의존하지 않는다.
- P1-02를 반영해 신규 anchor allocation 전에 active identity/history continuity를 검색하고, 단일 후보 재사용, identifier enrichment, collision quarantine, evidence 0일 때만 최초 anchor 선택, 후속 rekey 금지와 deterministic replay 규칙을 추가했다.
- provider price without canonical mapping, verified mapping promotion, fake regulatory ID prevention, ISIN/listDate enrichment, enrichment collision과 deterministic rebuild를 P0 문서 acceptance로 추가했다.
- ADR-011은 `PROPOSED — INDEPENDENT REVIEW P1-NOT-BLOCKING / AWAITING USER APPROVAL`, ADR-012는 `PROPOSED — REVISED AFTER INDEPENDENT REVIEW / AWAITING RE-REVIEW`로 유지했다. Codex가 어느 ADR도 새로 승인하지 않았다.
- 상태를 `CP3-A REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW / CP3-B NOT STARTED`로 갱신하고 자동 checkpoint 진행을 금지했다.

### Security and Scope

- documentation/contract-only 보완이며 application/test/fixture/migration/dependency/runtime config/API route/connector 변경 0
- actual credential 사용 0, actual Toss API 호출 0, account/order/WebSocket 변경 0
- CP3-B implementation, PR/main merge/tag/release 0

### Review

- independent review result: P0 0 / P1 2 / CP3-B not authorized
- 이 보완은 두 P1의 재검토를 요청하며 CP3-A 승인 또는 다음 checkpoint 승인을 선언하지 않는다.
- staged eight-file documentation set의 첫 full `scripts/test.ps1`은 exit 0이었다: backend 357/357, frontend 43/43, E2E 2/2, migration repeat/downgrade/re-upgrade, fixture second import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI, production build 2회, secret scan과 initial/final policy scan PASS.

## Unreleased — Phase 2 CP3-A Contract Checkpoint — 2026-08-24

### Added

- `plans/PHASE_02_CP3_A_CONTRACT.md`에 Security Master와 Current Price의 endpoint 역할, KR/US universe, provider staging identity, lifecycle, PriceSnapshot, source trace, hash/idempotency/revision, additive migration과 CP3-B/C/D acceptance 계약 추가
- ADR-012 `Toss provider security identity와 canonical issuer/security mapping 분리`를 `PROPOSED — AWAITING INDEPENDENT REVIEW`로 추가

### Changed

- Phase 2 실행계획을 현재 `CP1 PASS / CP2 COMPLETE / CP3-A IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW / CP3-B NOT STARTED` 상태로 정합화하면서 CP1 당시 조사 baseline과 현재 live verification matrix를 분리
- ADR-011을 `/prices timestamp=null`까지 표현하는 nullable observed time/date와 structured missing reason 계약으로 수정하되 `PROPOSED — REVISED FOR CP3-A / AWAITING INDEPENDENT REVIEW` 유지
- actual OAuth/stocks/success rate header만 `[LIVE_VERIFIED]`, `/stocks/all`, `/prices`, natural 429/5xx와 CP3 semantics/freshness는 `[LIVE_UNVERIFIED]`로 유지
- issuer identity, timestamp-null source semantics와 기존 source-record natural-key/revision 충돌을 Known Issues에 추가·갱신

### Security

- CP3-A는 문서·계약 checkpoint로 application/test/fixture/migration/dependency/runtime config/API route/connector 변경 0
- actual credential 조회·사용 0, actual Toss API 호출 0, account/order/WebSocket 변경 0, secret artifact 0
- CP3-B/C/D application implementation, PR/main merge/tag/release를 수행하지 않음

### QA

- current environment: PowerShell 7.6.4(최소 7.4.0 이상, previous final QA reference 7.6.5와의 accepted variance), Python 3.13.15, Node 24.19.0, npm 11.17.0, ASCII-only path
- 최종 staged documentation 기준 `scripts/test.ps1` exit code 0: backend 357/357, frontend 43/43, E2E 2/2, migration repeat/downgrade/re-upgrade, fixture 2차 import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI check, production build 2회, secret scan, initial/final policy scan PASS
- Toss preflight default와 SelfTest는 각각 external network requests 0이었고 default credential usage도 0
- 실패 이력 1: 첫 full run은 pre-existing orphaned workspace dev listeners가 3000/8000을 점유해 E2E 시작에서 exit 1이었다. 동일 repository command line을 확인한 exact process tree만 종료하고 포트 availability를 검증했다.
- 실패 이력 2: 두 번째 full run은 E2E 2/2 뒤 unstaged documentation 때문에 secret scan의 index/working-tree equality gate에서 exit 1이었다. scanner 예외를 추가하지 않고 허용 문서 7개만 stage한 뒤 전체 suite를 처음부터 재실행했다.

### Limitations

- CP3-A는 `PASS`, `APPROVED` 또는 `COMPLETE`가 아니다. ADR-011/ADR-012와 exact provider enum/identity/migration 결정은 GPT independent review와 사용자 승인을 기다린다.
- CP3-B는 `NOT STARTED`이며 자동으로 진행하지 않는다.

## Unreleased — Phase 2 CP2 Final Closeout — 2026-08-24

### Changed

- CP2-A~D final integrated QA를 완료하고 상태를 `CP2 COMPLETE / Phase 2 IMPLEMENTATION IN PROGRESS / CP3 NOT STARTED`로 갱신
- ADR-010을 `ACCEPTED`로 전환하고 exact REST allowlist, memory-only token, bounded retry, offline/live 분리 결정을 확정
- actual live 검증과 미검증 범위를 분리해 OAuth·stocks·성공 rate header만 `[LIVE_VERIFIED]`로 재분류
- Windows non-ASCII repository parent path의 setuptools editable build 실패를 `P2 DEFERRED / ENVIRONMENT CONSTRAINT`로 기록

### QA

- CP2-D2 사용자 독립 one-shot: provider drift `NO`, OpenAPI `3.1.0`, provider `1.2.14`, actual OAuth와 `GET /api/v1/stocks` PASS, allowed-IP 실행 경로와 Limit/Remaining/Reset header 유효성 PASS
- natural 429를 유도하지 않아 `Retry-After`는 `[LIVE_UNVERIFIED]` 유지; actual 429/5xx, production retry timing과 다른 market endpoint도 미검증 유지
- Vitest UTF-8 byte-safe exact 43 inventory 구현 commit `411749e171a717b3060973cb7b127fb94f592bab`
- ASCII-only 사용자 QA 환경 PowerShell 7.6.5, Python 3.13.15, Node 24.19.0, npm 11.17.0에서 backend 357/357, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, production build, secret scan, initial/final policy scan과 exit 0 확인

### Security

- closeout에서 live API를 재호출하거나 credential을 재사용·요청하지 않았고, actual credential 값·token·body·raw header 값을 문서·Git·QA evidence에 기록하지 않음
- P0 0, P1 0, unresolved functional P2 0; Windows path portability P2 1건은 workaround와 함께 명시적으로 이월

### Limitations

- CP2 완료는 Phase 2 완료가 아니다. CP3 이후 security master/current price, normalization, storage, freshness와 나머지 endpoint 구현은 시작하지 않았다.

## Unreleased — Phase 2 CP2-D1 — 2026-08-23

### Added

- `scripts/toss-live-preflight.ps1`의 safe default, offline `-SelfTest`, `-Live` + `-ConfirmReadOnly` + exact ACK three-way gate
- exact canonical OpenAPI runtime drift gate와 environment-only credential contract를 실행하는 internal Python runner/helper
- canonical OpenAPI GET 최대 1회, OAuth POST 최대 1회, `GET /api/v1/stocks` 최대 1회의 one-shot request budget
- OAuth/market 401·403·429·5xx, redirect, drift, safe output/redaction과 request count를 검증하는 MockTransport backend 테스트 36개

### Changed

- backend inventory를 321개에서 357개로 확대하고 standard `scripts/test.ps1`에 default와 offline SelfTest만 포함
- Toss connector source allowlist를 internal-only `preflight.py` exact filename까지 확대하고 control-plane manifest digest를 고정
- production retry/401 refresh 정책은 그대로 유지하면서 live preflight 전용 경로만 retry·refresh·replay 0회로 분리

### Security

- credential은 D2에서만 기존 server-only `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET` environment에서 읽고 CLI credential/token parameter와 `.env` loading을 제공하지 않음
- exact HTTPS origin·OpenAPI path·stocks endpoint만 허용하고 redirect 거부, TLS verification, `trust_env=False`, account/order/account header 금지를 유지
- PowerShell wrapper는 child stdout을 fixed key allowlist로 다시 필터링하고 provider body/message, raw header map, Authorization, credential, token, traceback과 private path를 출력·저장하지 않음
- D1 작업과 standard test에서 실제 credential 사용 0, OAuth POST 0, market GET 0; live evidence·DB·fixture·frontend·migration 변경 없음

### QA

- provider contract drift `NO`: OpenAPI `3.1.0`, REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`, exact origin 일치
- CP2-D1 baseline SHA `7437d8a30a6f2081431efee815ce96da85700f9b`, final validated implementation SHA `7840eee70ea3d4d8be9057904501ba277e68c99a`
- default `EXTERNAL_NETWORK_REQUESTS=0`, SelfTest `EXTERNAL_NETWORK_REQUESTS=0` 및 gate/schema/redaction/one-shot/drift-stop PASS
- Node.js 24.19.0에서 최종 `scripts/test.ps1` exit code 0: backend 357/357, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-D1 policy scan PASS
- D1 시작 전 승인된 anonymous canonical OpenAPI 문서 GET 1회만 수행했고 실제 credential, OAuth와 market business request는 수행하지 않음

### Limitations

- 실제 token issuance, 허용 IP, stocks response, rate-limit headers, provider timing, natural 429 `Retry-After`, edge/IP behavior는 계속 `[LIVE_UNVERIFIED]`다.
- CP2-D2는 `NOT STARTED`이며 CP2, CP2-D 또는 Phase 2 완료로 간주하지 않는다.

## Unreleased — Phase 2 CP2-C — 2026-08-23

### Added

- 12개 callable method/path를 7개 runtime group에 exact 매핑하는 `rate_limit.py`
- client×group shared async token bucket과 documented/observed/effective limit 분리
- 네 rate header만 읽는 strict integer parser와 memory-only missing/invalid/inconsistent diagnostic
- 총 3회 시도, 단일·누적 30초 상한, 1→2→4초 backoff와 bounded additive jitter timing primitive
- bounded 429 및 exact `500/502/503/504` retry, safe exhaustion/deferred typed error
- fake monotonic/sleeper/jitter와 `httpx.MockTransport` 기반 CP2-C backend 테스트 65개
- 429 Reset acquire wait와 backoff의 통합 누적 ceiling을 검증하는 deterministic backend 회귀 4개

### Changed

- OAuth `/oauth2/token`을 shared `AUTH` limiter와 같은 bounded retry policy에 연결
- market GET의 401 generation-aware refresh/replay는 1회를 유지하면서 rate retry budget을 분리
- Toss connector source allowlist를 exact 7개 Python 파일로 고정하고 backend inventory를 252개에서 317개로 확대
- 독립 검토 P2 수정으로 429 이후 재시도의 limiter acquire wait를 같은 operation `_RetryBudget`에 포함하고 backend inventory를 321개로 확대
- missing/invalid `Retry-After`에서 유효한 Reset이 잔여 single/cumulative budget을 넘으면 대기를 자르지 않고 즉시 safe deferred error로 종료

### Security

- public token manager/lease/raw bearer surface 없이 token을 connector-private memory에 유지
- response header 전체를 저장하지 않고 `X-RateLimit-Limit`, `Remaining`, `Reset`, `Retry-After`만 숫자로 관찰
- provider body/message, Authorization, Cookie, Set-Cookie, credential과 uncontrolled URL을 rate state/error에 보존하지 않음
- 400/401 규칙 외 auth error/403/404/422/501/contract/transport/boundary error는 retry하지 않음
- actual credential, actual Toss request, account/order surface와 CP2-D live script를 추가하지 않음

### QA

- provider contract drift `NO`: OpenAPI `3.1.0`, REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- implementation commit `e0017a1891b8f7048c5dc97565224749cf287989`
- P2 cumulative-wait hardening implementation commit `fe65076021f2cc9b3c8d533c3e844b9b9699d5b9`
- Node.js 24.19.0, npm 11.17.0에서 최종 `scripts/test.ps1` exit code 0
- backend 321/321, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-C policy scan PASS
- standard test outbound network 0; retry constants와 무관하게 connector target 144개가 약 1초에 완료

### Limitations

- 실제 OAuth/token, 허용 IP, runtime rate header·Retry-After, provider response/error와 timing은 계속 `[LIVE_UNVERIFIED]`다.
- CP2-D live preflight는 `NOT STARTED`이며 `scripts/toss-live-preflight.ps1`을 만들지 않았다.
- CP2-C PASS는 CP2 또는 Phase 2 완료를 의미하지 않는다.

## Phase 2 CP2-B — 2026-08-23

### Added

- strict OAuth token/error 모델과 backend application-owned single token manager
- memory-only token lease, monotonic expiry, bounded safety margin, explicit·generation-aware invalidation
- exact Toss origin과 enum 기반 11개 market GET path만 노출하는 `httpx.AsyncClient` transport
- streaming response ceiling(OAuth 64 KiB, market JSON 32 MiB), content-type/JSON/redirect 안전 검사
- CP2-B auth·boundary·integration·concurrency 테스트 75개

### Changed

- Toss connector source allowlist를 CP2-B의 exact 6개 Python 파일로 발전
- backend inventory를 176개에서 251개로 확대하고 통합 gate 기대값을 갱신
- ADR-010은 `PROPOSED`를 유지하면서 CP2-A/CP2-B 구현 진행 메모를 추가

### Security

- `trust_env=False`, `follow_redirects=False`, TLS verification 고정과 connect/read/write/pool timeout을 적용
- 외부 arbitrary URL/method/header API 없이 POST는 내부 `/oauth2/token` 하나로 제한
- symbol traversal/scheme injection과 raw query string, unknown query key/value를 fail closed
- market GET Authorization을 transport 내부에서만 구성하고 token POST·query·Cookie에 전달하지 않음
- 401 `expired-token`/`invalid-token`만 generation-aware invalidate 후 최대 한 번 재발급·replay
- provider body/message, credential, token을 exception/log/raw/DB/QA evidence에 저장하지 않음

### QA

- provider contract drift `NO`: REST API `1.2.14`, canonical SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`
- implementation commit `6a823edc6b3e02cf1c06778f26045f7c535066ed`
- Node.js 24.19.0, npm 11.17.0에서 최종 `scripts/test.ps1` exit code 0
- backend 251/251, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, build 2회, secret scan, CP2-B policy scan PASS
- standard test outbound network 0; 모든 Toss connector test는 합성 credential과 `httpx.MockTransport` 사용

### Limitations

- 실제 credential, token endpoint, market endpoint는 호출하지 않아 live OAuth·허용 IP·response/rate header는 계속 `[LIVE_UNVERIFIED]`다.
- CP2-C rate limiter·429/5xx retry와 CP2-D live preflight는 시작하지 않았다.

## Phase 2 CP2-A — 2026-08-23

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
