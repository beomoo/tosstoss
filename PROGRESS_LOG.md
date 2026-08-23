# Progress Log

## 2026-08-16 — Phase 1 계획과 최초 구현

- Phase 0 문서 검토를 마치고 `plans/PHASE_01_EXECUTION_PLAN.md`와 Foundation brief를 승인된 구현 범위로 확정했다.
- 실제 투자 데이터, 계좌, 주문, 자동매매, OpenAI API, 외부 connector를 제외하고 합성 fixture 기반 읽기 전용 Foundation을 구현했다.
- FastAPI/Pydantic API, SQLite migration, 멱등 fixture import, Next.js Company/Data Quality 화면, OpenAPI 계약과 Windows PowerShell 실행 스크립트를 추가했다.
- 최초 자체 QA에서 setup 재실행, 백엔드·프런트엔드·E2E, 빌드, migration, fixture 멱등성, 보안·정책 경계를 확인했다.

## 2026-08-22 — Phase 1 계약·보안·실행 경계 강화

- strict 계약, 오류 envelope, UTC/Decimal 정밀도, source revision, fixture manifest와 API/UI 상태 표현을 보강했다.
- 외부 네트워크 차단, localhost 고정, 브라우저 transport 수집, 프로세스 소유권 정리, 테스트 inventory와 제어 파일 digest를 fail-closed 방식으로 강화했다.
- 최종 테스트 inventory를 backend 172개, frontend 43개, E2E 2개로 고정했다.
- PowerShell AST, Python/Ruff/mypy, ESLint/TypeScript, OpenAPI drift, Next production build 검사를 통합 게이트에 포함했다.

## 2026-08-22 — Windows Node.js 네이티브 충돌 조사

- 시스템 Node.js 24.15.0에서 짧은 loopback HTTP 연결 중 `0xC0000409` 네이티브 종료를 재현했다.
- 프로세스 cleanup Job 없이도 재현되고 Node.js 24.19.0에서는 반복 재현되지 않아 cleanup 경합을 원인에서 제외했다.
- Node.js 공식 이슈 `#63620`과 수정 PR `#62561`에 부합함을 확인하고 지원 하한을 24.16.0, 재현 기준을 24.19.0으로 변경했다.
- `.node-version`, package engine, npm 버전을 고정하고 모든 PowerShell 진입점에서 정확한 `node.exe`/`npm.cmd` 경로와 상속 `NODE_OPTIONS`를 fail-closed로 검증하도록 했다.
- 시스템 Node.js는 변경하지 않고 공식 portable Node.js 24.19.0으로 최종 QA를 수행했다. 공식 ZIP SHA-256은 `57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73`과 일치했다.

## 2026-08-22 — 최종 실행과 결과 회수

- 구현 기준 commit `f358fa3f0d1af44d0348bc5ba5c48be7866d7b21`에서 `scripts/setup.ps1`을 2회 연속 실행해 모두 통과했다.
- `scripts/dev.ps1 -Smoke`에서 Web 200, `/health` 정상, API JSON 로그 14줄, 종료 후 3000/8000 포트와 소유 프로세스 0개를 확인했다.
- 통합 `scripts/test.ps1`에서 다음 결과를 회수했다.
  - 포맷/Ruff/ESLint, mypy 40개 소스, TypeScript와 경로 타입 통과
  - 프로세스 cleanup canary 20회 통과
  - backend 172/172, frontend 43/43, E2E 2/2 통과
  - migration 반복/downgrade/re-upgrade, fixture 2차 import `inserted=0`, `updated=0`, `unchanged=13` 통과
  - OpenAPI drift 0, Next.js production build 2회 통과
- 통합 실행의 마지막 비밀정보 검사에서 `package-lock.json` 승인 digest가 이전 Node engine 값에 남아 있음을 확인했다. 잠금 파일은 `npm ci` 2회와 정책 스캐너의 독립 digest 검증을 이미 통과한 동일 파일이었다.
- 전체 테스트를 중복 실행하지 않고 `secret-scan.ps1`의 승인 lock digest를 실제 추적 파일 SHA-256 `f5cf022dd418c03974095c1f8f703c84648a90edff7edbb22c13fb2a27614a67`로 맞췄으며, 연동된 59개 제어 파일 digest를 `101ee6d95db34955d05c634d6e7d29564f93ea06ba0ff960e9f0a649249912ed`로 갱신했다.
- 최종 Playwright 화면, setup/dev/test 로그와 기존 sample JSON을 `qa/evidence/phase_01`에 회수했다.

## 2026-08-23 — Phase 1 종료

- Phase 1 독립 검증을 최종 PASS했으며 최종 검증 commit은 `57b2a63ead06d03191d8094e1689b8d2ab3d7764`다.
- PR #1을 통해 merge commit `b1829a7375704271a21267e1fcf62808147be593`으로 `main`에 병합했다.
- Phase 1 완료 기준을 annotated tag `v0.1.0`으로 고정했다.
- Phase 1 feature branch는 merge 포함 여부 확인 후 정리했다.
- Phase 2 구현은 시작하지 않았으며, 전용 실행계획 작성·검토가 다음 구현 전 게이트다.

## 현재 중지 지점

- Phase 1: `COMPLETE`
- Independent QA: `PASS`
- PR: `#1`
- Merge commit: `b1829a7375704271a21267e1fcf62808147be593`
- Release baseline tag: `v0.1.0`
- Phase 2: 구현 미착수

## 2026-08-23 — Phase 2 CP2-A 보안 경계 구현

- 시작 branch는 `feature/phase-02-toss`, baseline SHA는 `e2c0db5e007aca4ed10c0037554ba1ee6eb5a389`였고 작업트리는 clean이었다.
- 목적은 실제 Toss 요청을 만들지 않고, 향후 읽기 전용 Toss connector만 좁게 허용하면서 다른 외부 HTTP·provider·계좌·주문 surface를 계속 fail-closed로 유지하는 것이었다.
- 코드 변경 전 공식 canonical OpenAPI를 재확인했다. REST API version `1.2.14`, SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`, server origin, 12개 callable method/path, OAuth schema, 9개 rate group이 CP1 기준과 같아 `PROVIDER_CONTRACT_DRIFT=NO`로 판정했다.
- `connectors/toss` namespace scaffold만 추가했고 OAuth, token manager, HTTP request, retry, rate limiter, live preflight는 구현하지 않았다.
- `httpx==0.28.1`을 개발 전용 항목에서 exact runtime dependency로 승격했다. `requirements.in`과 hash-pinned `requirements.lock`에는 이미 같은 direct dependency가 있어 lock bytes와 승인 SHA-256 `77c659d879ecc4ed595e790b1af3b747353c6494a85d1ec821bdf0ac0a1b552d`는 바뀌지 않았다. 설치된 metadata의 Python 요구사항은 `>=3.8`이고 저장소 Python `>=3.13.1,<3.14`와 호환된다.
- optional server-only `TOSS_CLIENT_ID`, `TOSS_CLIENT_SECRET` 설정을 secret-aware type으로 추가하고, 누락·빈 값 startup과 repr·validation error·structured log 비노출을 검증했다. `.env.example`에는 빈 이름만 추가했으며 실제 credential과 `.env` 파일은 만들지 않았다.
- policy scan에 exact Toss origin, 12개 callable endpoint/rate metadata, Toss namespace 전용 `httpx` import, frontend 직접 접근 금지, 계좌·주문 endpoint, account header, generic connector, `NEXT_PUBLIC_TOSS_*`, OpenAI 금지 카나리를 추가했다.
- secret scan에 Toss secret assignment, generic client secret assignment, Authorization Bearer 합성 카나리를 추가했고 `.env.local`, `.env.development.local` ignore 검증을 보강했다.
- 수정 파일은 `.env.example`, `pyproject.toml`, `config.py`, `logging_config.py`, connector namespace 2개, policy/secret/test 스크립트, backend 보안 테스트 3개와 Phase 2 실행계획이다. DB migration, fixture, frontend application source는 변경하지 않았다.
- 테스트 inventory는 backend `176`개, frontend `43`개, E2E `2`개로 증가·유지했다.
- 최종 `scripts/test.ps1`은 Node.js `24.19.0`, npm `11.17.0`에서 exit code `0`으로 통과했다. backend 176/176, frontend 43/43, E2E 2/2, migration 왕복, fixture 2차 import `inserted=0`, `updated=0`, `unchanged=13`, OpenAPI drift, production build 2회, secret scan, policy scan이 모두 PASS했다.
- 시도 이력과 실패 지점을 숨기지 않는다. 첫 실행은 시스템 Node.js `24.15.0` 안전 하한에서 정상 차단됐고, 다음 실행은 Ruff 포맷 2개 파일에서 중단됐다. 이후 저장소 내부에 둔 검증용 ZIP/캐시를 secret scan이 거부해 저장소 밖으로 이동했고, 합성 credential test 2줄도 secret scanner가 거부해 예외 추가 없이 canary 구성 방식을 수정했다. 한 통합 실행에서 기존 E2E local RSC prefetch 검사 race가 1회 발생했으나 무변경 단독 재실행과 최종 전체 실행에서 모두 2/2 PASS했다.
- 미해결 항목은 CP2-B OAuth/token/HTTP client, CP2-C rate/retry/error taxonomy, CP2-D live preflight와 최종 CP2 acceptance다. CP2-A 범위의 P0/P1 결함은 없다. E2E prefetch timing 1회 관찰은 후속 회귀에서 모니터링한다.
- 마지막 정상 baseline SHA: `e2c0db5e007aca4ed10c0037554ba1ee6eb5a389`
- CP2-A final validated implementation SHA: `e1bca561998d745bb357dc8c92f835926886e770`
- CP2-B 시작 여부: `NO`

## 현재 중지 지점 — Phase 2 CP2-A

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2-A: `PASS`
- CP2-B: `NOT STARTED`
- 실제 Toss API 요청: `없음`
- 실제 credential 사용: `없음`

## 2026-08-23 — Phase 2 CP2-B OAuth + exact HTTP boundary

- 시작 branch는 `feature/phase-02-toss`, rollback base는 `aa779cac5839dad260a2001eaea6661fd9bbe216`이었고 작업트리는 clean이었다. reset, rebase, force push, cherry-pick은 사용하지 않았다.
- application code 변경 전 canonical OpenAPI를 새로 확인했다. OpenAPI `3.1.0`, REST API `1.2.14`, SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`, exact origin, OAuth/error schema, 12개 callable endpoint와 rate metadata가 승인 기준과 동일해 `PROVIDER_CONTRACT_DRIFT=NO`로 판정했다.
- `auth.py`, `client.py`, `errors.py`, `models.py`를 추가하고 Toss package export를 갱신했다. dependency, DB migration, fixture, frontend application source와 public route는 변경하지 않았다.
- application-owned `TossHttpClient` 하나가 connector-private token manager 하나를 소유한다. token/monotonic expiry는 process memory에만 두고 startup/import에서 발급하지 않으며 credential 누락·partial 상태는 실제 issuance 시 structured error로 fail closed한다.
- token 응답은 extra-forbid strict model로 `access_token`, exact `Bearer`, positive strict integer `expires_in`을 검증한다. token은 `SecretStr`/private lease로 감싸 repr·error·log·DB·raw·QA evidence에 노출하지 않는다.
- 100 concurrent `get_token()`에서 OAuth POST 1회, issuance 실패 후 lock release, cancellation 후 재호출, short TTL bounded margin, expiry 재발급, explicit/generation-aware invalidation을 deterministic하게 검증했다.
- HTTP transport는 `https://openapi.tossinvest.com`과 11개 enum market GET path만 외부 API로 노출한다. POST는 내부 `/oauth2/token` 하나뿐이며 raw URL/method/query string/header override API가 없다.
- `trust_env=False`, redirects disabled, TLS verification enabled, connect/write/pool 5초·read 10초 timeout, OAuth 64 KiB·market JSON 32 MiB streaming ceiling을 고정했다. token POST에는 Bearer를 넣지 않고 market GET에만 내부 Authorization을 구성한다.
- 401은 exact `expired-token`/`invalid-token`만 최대 한 번 invalidate→single-flight reissue→GET replay한다. 24개 동시 expired request의 refresh issuance 한 generation과 뒤늦은 이전 generation 401이 새 token을 무효화하지 않는 race를 검증했다. 403, 429, 500은 typed error로 한 번 반환하며 CP2-C retry는 구현하지 않았다.
- 테스트 inventory는 backend 176개에서 251개로 증가했고 frontend 43개, E2E 2개는 유지했다. CP2-A empty namespace snapshot은 삭제하지 않고 exact CP2-B connector source allowlist 테스트로 발전시켰다.
- 실패·수정 이력: 첫 통합 실행은 수동 Ruff 실행이 만든 `.ruff_cache`를 secret scan이 거부해 exit 1이었다. cache를 제거한 두 번째 통합 실행은 수동 mypy의 `.mypy_cache`와 합성 credential 표현을 secret scan이 거부해 exit 1이었다. 스캐너 예외를 추가하지 않고 cache 제거, 합성 값 분할과 안전한 변수명으로 수정했으며 독립 secret scan PASS 후 전체 회귀를 처음부터 다시 실행했다.
- 최종 `scripts/test.ps1`은 Node.js 24.19.0, npm 11.17.0에서 exit code `0`으로 통과했다. backend 251/251, frontend 43/43, E2E 2/2, migration 왕복, fixture 2차 import `inserted=0`, `updated=0`, `unchanged=13`, OpenAPI drift, production build 2회, secret scan, CP2-B policy scan이 모두 PASS했다.
- standard test outbound network는 0이었다. 모든 connector test는 synthetic credential과 `httpx.MockTransport`만 사용했으며 실제 Toss token/market 요청과 실제 credential 사용은 없었다.
- 초기 종료 시 CP2-B 범위 P0/P1/P2 결함이 없다고 기록했으나, 후속 독립 검토에서 아래 P2 token-boundary 노출 1건이 발견·수정됐다. live OAuth, 허용 IP, 실제 response/rate header는 `[LIVE_UNVERIFIED]`로 남는다.
- CP2-B rollback base: `aa779cac5839dad260a2001eaea6661fd9bbe216`
- CP2-B validated implementation SHA: `6a823edc6b3e02cf1c06778f26045f7c535066ed`
- rollback 필요: `NO`; revert commit: `없음`
- CP2-C started: `NO`

## 현재 중지 지점 — Phase 2 CP2-B

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2-A: `PASS`
- CP2-B: `PASS`
- CP2-C: `NOT STARTED`
- 실제 Toss API 요청: `없음`
- 실제 credential 사용: `없음`

## 2026-08-23 — Phase 2 CP2-B P2 token-boundary 보안 하드닝

- 독립 검토에서 `TossHttpClient.token_manager` public property를 통해 application caller가 token manager와 lease에 접근하고, lease의 raw Authorization value extraction 메서드까지 호출할 수 있는 P2 1건을 발견했다.
- public `token_manager` accessor를 제거하고 manager field를 `TossHttpClient`의 name-mangled private implementation으로 바꿨다. token manager와 lease 타입도 connector-private 타입으로 축소했다.
- raw bearer token을 반환하는 메서드를 삭제했다. private lease는 connector-internal capability key가 있을 때 transport request에 Authorization을 직접 적용하고 raw token이나 header value를 반환하지 않는다.
- token manager 단위 테스트는 production client accessor 대신 `auth.py`의 `MockTransport` 전용 internal test seam을 사용하도록 전환했다. 100 concurrency single-flight, monotonic expiry, explicit/generation-aware invalidation, 동시·지연 401 replay의 검증 의미는 유지했다.
- application runtime에 `.token_manager`, public token manager/lease 타입, raw extraction 메서드가 다시 나타나면 실패하는 backend negative test와 policy canary를 추가했다. backend inventory는 252개가 됐다.
- 첫 전체 실행은 backend 252/252, frontend 43/43, migration/fixture/OpenAPI, build 2회, E2E 2/2까지 통과한 뒤 secret scan의 index/working-tree 동일성 전제에서 정상 차단됐다. 변경을 stage하고 전체 `scripts/test.ps1`을 처음부터 재실행했다.
- 최종 전체 실행은 Node.js 24.19.0, npm 11.17.0에서 exit code `0`이었다. backend 252/252, frontend 43/43, E2E 2/2, migration 왕복, fixture idempotency, OpenAPI drift, production build 2회, secret scan, CP2-B policy scan이 모두 PASS했다.
- CP2-C rate limiter/retry는 시작하거나 구현하지 않았다. 실제 Toss 요청과 실제 credential 사용도 없었다.
- CP2-B P2 security hardening final validated implementation SHA: `94488f7caccd747b47d7d9f1d6546840dfb14b4b`
- CP2-C started: `NO`

## 현재 중지 지점 — Phase 2 CP2-B P2 hardening

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2-B: `PASS`
- CP2-B P2 hardening: `PASS`
- CP2-C: `NOT STARTED`
- 실제 Toss API 요청: `없음`
- 실제 credential 사용: `없음`
