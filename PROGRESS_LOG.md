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

## 2026-08-23 — Phase 2 CP2-C Rate Limit + Retry + Error Taxonomy

- 시작 branch는 `feature/phase-02-toss`, CP2-C baseline SHA는 `8848af0739651f5cd49a7e791bbd055301599f19`였고 local/origin SHA가 일치했으며 작업트리는 clean이었다. reset, rebase, force push는 사용하지 않았다.
- application code 변경 전 canonical OpenAPI를 다시 다운로드했다. OpenAPI `3.1.0`, REST API `1.2.14`, SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`, origin `https://openapi.tossinvest.com`, 12개 callable method/path와 group, OAuth endpoint, 429 reference, 네 rate header integer schema, callable 500 error schema가 CP1/CP2 기준과 같아 `PROVIDER_CONTRACT_DRIFT=NO`로 판정했다.
- `rate_limit.py`에 7개 runtime group과 documented TPS를 고정했다: `AUTH=5`, `STOCK=5`, `STOCK_ALL=1`, `STOCK_TRADING_TREND=10`, `MARKET_INFO=3`, `MARKET_DATA=15`, `MARKET_DATA_CHART=20`. support-only indicator group은 runtime에 활성화하지 않았다.
- `TossHttpClient` 하나가 모든 group의 `_TossRateLimiter` 하나를 소유한다. group별 독립 lock/state를 가진 monotonic async token bucket을 request 전 통과하며, 같은 group endpoint는 bucket을 공유하고 다른 group은 서로 block하지 않는다.
- `documented_limit`, 최신 유효 `observed_limit`, 둘 중 작은 `effective_limit`을 분리했다. 낮은 observed limit은 즉시 capacity를 줄이고, 더 큰 provider 값은 documented ceiling을 넘겨 확장하지 않는다.
- allowlisted telemetry는 `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After` 네 값뿐이다. Limit은 ASCII integer `1..10000`, Remaining은 `0..10000`이면서 limit 이하, Reset/Retry-After는 integer seconds `0..86400`으로 검증한다. NaN, infinity, sign, decimal, whitespace, 음수와 상한 초과를 거부한다.
- 정상 payload의 missing/malformed/inconsistent rate header는 성공 자체를 실패로 바꾸지 않고 memory-only `RATE_HEADERS_MISSING`, `RATE_HEADERS_INVALID`, `RATE_HEADERS_INCONSISTENT` diagnostic과 safe numeric snapshot만 남긴다. response headers, body, message, Authorization, Cookie, Set-Cookie는 state/error에 복사하지 않는다.
- retry 상수는 승인 계획대로 최초 포함 `MAX_TOTAL_ATTEMPTS=3`, `MAX_SINGLE_RETRY_SLEEP_SECONDS=30`, `MAX_CUMULATIVE_RETRY_SLEEP_SECONDS=30`, initial backoff `1s`다. 지수식은 `1→2→4...`이고 base에 `[0, base]` 범위의 additive jitter를 더하며 private deterministic source를 주입할 수 있다.
- 429는 strict provider error envelope와 exact `rate-limit-exceeded`/`edge-rate-limit-exceeded`를 확인한 뒤 유효한 `Retry-After`를 jitter 없이 우선한다. header가 missing/invalid면 bounded exponential backoff를 사용한다. 30초를 넘거나 누적 상한을 넘는 유효 권고는 짧게 잘라 조기 retry하지 않고 `TossRetryDeferredError`로 반환하며 shared group block state를 보수적으로 유지한다.
- transient retry status는 exact `{500, 502, 503, 504}`, provider code는 exact `{internal-error, maintenance}`다. 반복 실패는 safe endpoint template/group/status/code/request ID/attempt metadata만 가진 `TossRetryExhaustedError`로 종료한다. 501이나 unknown code는 자동 retry 대상으로 넓히지 않았다.
- 400/403/404/422, invalid client/access denied, malformed OAuth/provider envelope, malformed JSON/content type, schema mismatch, redirect, response-too-large, boundary error는 retry하지 않는다. `TossTransportError`도 CP2-B 동작을 유지해 connect/read/timeout evidence 없이 retry 대상으로 확대하지 않았다.
- OAuth POST는 shared `AUTH` limiter와 같은 bounded 429/transient policy를 사용하지만 token manager single-flight lock 안에서만 수행한다. 100 concurrent caller + OAuth 429에서도 HTTP issuance attempt는 budget에 따른 2회, token generation은 1개였다.
- GET 401은 기존 exact expired/invalid token 규칙과 replay 최대 1회를 유지한다. `GET→401→refresh OAuth 429→AUTH retry→token success→GET replay`에서 token POST 3회(초기 포함), market GET 2회만 발생함을 검증했다.
- backend inventory는 252개에서 317개로 65개 증가했다. CP2-C connector target 140개는 fake clock/sleeper/jitter와 `httpx.MockTransport`로 약 1초에 완료됐고, 전체 backend 317/317도 통과했다. frontend 43개와 E2E 2개 inventory는 감소하지 않았다.
- failure/fix 이력: 첫 target run은 기존 24-concurrency 401 test에서 token refill의 부동소수점 경계가 fake clock 해상도보다 작은 wait를 반복해 정체됐다. 실행을 중단하고 token epsilon과 최소 async throttle interval을 추가했으며 해당 회귀와 target 140개가 통과했다.
- failure/fix 이력: 수동 pytest가 만든 `__pycache__` 때문에 첫 policy scan이, 수동 Ruff/mypy cache 때문에 첫 secret scan이 정상 차단됐다. scanner 예외를 추가하지 않고 exact generated cache만 제거했으며 policy/secret scan을 처음부터 재실행해 통과했다.
- failure/fix 이력: 첫 전체 `scripts/test.ps1`은 system Node.js 24.15.0 안전 하한에서 application test 전에 정상 차단됐다. 시스템 Node를 바꾸지 않고 기존 공식 portable Node.js 24.19.0/npm 11.17.0을 해당 프로세스 PATH에만 사용해 전체 실행을 다시 시작했다.
- 최종 문서 포함 `scripts/test.ps1`은 Node.js 24.19.0, npm 11.17.0에서 exit code `0`으로 통과했다. backend 317/317, frontend 43/43, E2E 2/2, migration 왕복, fixture 2차 import `inserted=0`, `updated=0`, `unchanged=13`, OpenAPI drift, production build 2회, secret scan, CP2-C policy scan이 모두 PASS했다.
- standard test outbound Toss request는 0이었다. 실제 credential, OAuth token, market API, 실제 rate header·Retry-After와 provider timing은 사용·검증하지 않아 `[LIVE_UNVERIFIED]`를 유지한다.
- CP2-C final implementation SHA: `e0017a1891b8f7048c5dc97565224749cf287989`
- CP2-D started: `NO`

## 현재 중지 지점 — Phase 2 CP2-C

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2-A: `PASS`
- CP2-B: `PASS`
- CP2-B P2 hardening: `PASS`
- CP2-C: `PASS`
- CP2-D: `NOT STARTED`
- 실제 Toss API 요청: `없음`
- 실제 credential 사용: `없음`

## 2026-08-23 — Phase 2 CP2-C 독립 검토 P2 cumulative-wait hardening

- 시작 branch는 `feature/phase-02-toss`, baseline/local/origin SHA는 `e60872e28c30502b9cb5477922c34f1ce05d6827`이었고 작업트리는 clean이었다. reset, rebase, force push는 사용하지 않았다.
- 독립 검토에서 429의 `X-RateLimit-Remaining=0`과 유효한 `X-RateLimit-Reset`이 만든 다음 시도 `_TossRateLimiter.acquire()` 대기가 `_RetryBudget.cumulative_sleep_seconds`에 포함되지 않는 P2 1건을 확인했다. 이 때문에 missing/invalid `Retry-After`가 반복되면 backoff 1초+2초만 기록하면서 Reset block으로 실제 fake/production 요청 경로가 누적 30초 ceiling을 우회할 수 있었다.
- 최초 정상 요청의 선제적 local throttling은 기존대로 retry budget과 분리했다. 429 이후 재시도 시도의 limiter acquire에는 같은 operation budget을 전달해 실제 acquire wait를 backoff/Retry-After wait와 함께 기록한다.
- missing/invalid `Retry-After`에서 `Remaining=0`과 유효한 Reset이 있으면 Reset 전체가 현재 잔여 single/cumulative budget 안인지 retry 결정 시 먼저 검사한다. 초과하면 짧게 잘라 sleep하거나 premature retry하지 않고 shared block state를 보존한 `TossRetryDeferredError`로 즉시 종료한다. 동시 상태 변화로 acquire 시점 block이 늘어난 경우도 같은 ceiling 검사로 fail closed한다.
- deterministic 회귀 4개를 추가했다: `429 + missing Retry-After + Reset=30` 반복, OAuth 429의 invalid `Retry-After + Reset=31`, 누적 ceiling 정확히 직전/직후, fake sleeper 총합이 `MAX_CUMULATIVE_RETRY_SLEEP_SECONDS=30` 이하임을 검증한다. connector target은 140개에서 144개, backend inventory는 317개에서 321개로 증가했다.
- 수정 중 실패/은폐 이력은 없다. target connector `144/144`, mypy 47 source, 전체 backend `321/321`, CP2-C policy scan이 통과했다. 수동 검사 생성 캐시는 scanner 예외 없이 exact generated directory만 정리했다.
- 최종 `scripts/test.ps1`은 Node.js 24.19.0, npm 11.17.0에서 exit code `0`으로 통과했다. backend 321/321, frontend 43/43, E2E 2/2, migration 왕복, fixture 2차 import `inserted=0`, `updated=0`, `unchanged=13`, OpenAPI drift, production build 2회, secret scan, CP2-C policy scan이 모두 PASS했다.
- standard test outbound Toss request는 0이었다. 실제 credential, OAuth token, market API, 실제 rate header·Retry-After·Reset과 provider timing은 사용·검증하지 않아 `[LIVE_UNVERIFIED]`를 유지한다.
- CP2-C P2 hardening final implementation SHA: `fe65076021f2cc9b3c8d533c3e844b9b9699d5b9`
- CP2-D started: `NO`

## 현재 중지 지점 — Phase 2 CP2-C P2 hardening

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2-A: `PASS`
- CP2-B: `PASS`
- CP2-B P2 hardening: `PASS`
- CP2-C: `PASS`
- CP2-C P2 cumulative-wait hardening: `PASS`
- CP2-D: `NOT STARTED`
- 실제 Toss API 요청: `없음`
- 실제 credential 사용: `없음`

## 2026-08-23 — Phase 2 CP2-D1 Safe Live Preflight Tooling + Offline Validation

- 시작 branch는 `feature/phase-02-toss`, `CP2_D1_BASELINE_SHA`는 `7437d8a30a6f2081431efee815ce96da85700f9b`였고 local/origin SHA가 일치했으며 작업트리는 clean이었다. `fe65076021f2cc9b3c8d533c3e844b9b9699d5b9`는 baseline의 ancestor였고 이후 변경은 `STATUS.md`, `CHANGELOG.md`, `PROGRESS_LOG.md`, `KNOWN_ISSUES.md`, `DECISIONS.md`뿐이었다. reset, rebase, force push는 사용하지 않았다.
- D1 코드 변경 전에 exact `https://openapi.tossinvest.com/openapi-docs/latest/openapi.json`을 redirect·proxy 없이 memory-only로 1회 다운로드했다. OpenAPI `3.1.0`, REST API `1.2.14`, SHA-256 `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a`, exact server origin이 승인 기준과 일치했다. 전체 document hash가 동일하므로 OAuth endpoint/schema, 12개 callable method/path와 rate group, rate-limit response/header schema, error envelope, 401/403/429/5xx contract도 byte-identical이며 `PROVIDER_CONTRACT_DRIFT=NO`다.
- 목적은 actual credential을 쓰기 전에 secret·token·provider body를 노출하거나 계좌·주문을 호출하거나 retry할 수 없는 one-shot live preflight를 offline에서 검증해 `LIVE TOOL IMPLEMENTED / LIVE CALL NOT EXECUTED` 상태를 만드는 것이었다.
- 추가 파일은 `scripts/toss-live-preflight.ps1`, `scripts/toss_live_preflight_runner.py`, internal-only `services/api/src/toss_dashboard_api/connectors/toss/preflight.py`, `tests/backend/test_toss_preflight.py`다. `scripts/test.ps1`, `scripts/policy-scan.ps1`, `tests/backend/test_no_external_network.py`만 최소 수정했으며 DB, storage, migration, fixture, frontend, scheduler와 public API/route는 변경하지 않았다.
- live opt-in은 `-Live`, `-ConfirmReadOnly`, exact process environment ACK `TOSS_LIVE_PREFLIGHT_ACK=READ_ONLY_ONE_SHOT`의 3중 gate다. 기본 실행은 `LIVE_NOT_REQUESTED`, `-SelfTest`는 offline synthetic mode이며 둘을 함께 사용할 수 없다.
- symbol은 non-secret `-Symbol` 또는 `TOSS_PREFLIGHT_SYMBOL`만 사용하고 `^[A-Za-z0-9.\-]+$`, 최대 32자로 제한한다. credential은 D2에서만 기존 server-only `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET` process environment에서 읽으며 credential/token CLI parameter와 `.env` loading은 없다. D1 test child에서는 두 credential environment를 빈 값으로 override하고 parent environment를 변경·조회·출력하지 않았다.
- runtime 순서는 flags → ACK → symbol → canonical contract GET → drift NO → credential 존재 검증 → OAuth → stocks GET → safe summary다. canonical exact origin/path/version/SHA가 다르면 `PROVIDER_CONTRACT_DRIFT=YES`로 중단해 OAuth 0, market 0을 보장하며 expected contract는 자동 갱신하지 않는다.
- live network budget은 canonical OpenAPI GET 최대 1, OAuth POST 최대 1, `GET /api/v1/stocks` 최대 1이다. preflight OAuth/market retry는 0, 401 token refresh/replay는 0이다. production `TossHttpClient`의 bounded 429/5xx retry, AUTH single-flight와 generation-aware 401 replay는 변경하지 않았다.
- exact HTTPS origin, TLS verification, `trust_env=False`, redirects disabled, OpenAPI exact path와 stocks endpoint 하나만 허용한다. account/order endpoint, `X-Tossinvest-Account`, arbitrary URL/method/header, public token manager/lease/raw bearer surface는 계속 접근 불가다.
- live stdout은 fixed `KEY=VALUE` allowlist만 허용하며 credential configured 여부, safe stage/category/status/code와 rate header present/valid 상태만 표현한다. client ID/secret, token, Authorization, provider message/body, raw headers, traceback, private absolute path와 response/evidence file은 출력·저장하지 않는다.
- `-SelfTest` 결과는 `EXTERNAL_NETWORK_REQUESTS=0`, gate validation, output schema, redaction, one-shot, drift stop 모두 `PASS`였다. default invocation도 `EXTERNAL_NETWORK_REQUESTS=0`, `CREDENTIALS_USED=0`, `LIVE_NOT_REQUESTED`였다.
- MockTransport로 OAuth/market 성공 exactly 1+1, OAuth 401/403/429/5xx, market 401/429/5xx, contract drift, redirect, rate header complete/missing/invalid, response/token/header redaction과 forbidden surface를 검증했다. backend inventory는 321개에서 357개로 증가했고 production retry 및 CP2-C cumulative-wait 회귀도 함께 통과했다.
- 실패·수정 이력을 숨기지 않는다. 초기 전체 실행들은 수동 검사에서 생긴 `.ruff_cache`/`.mypy_cache`와 공개 계약 SHA·credential 존재 변수 표현을 secret scanner가 fail-closed로 거부했다. scanner 예외를 추가하지 않고 cache를 저장소 밖 격리 경로로 이동하고 표현을 안전하게 수정했다. 이후 전체 실행은 신규 Python 2개 Ruff format check에서 중단됐고, 포맷 적용 뒤 exact 65-file policy manifest digest가 변경되어 한 번 더 fail-closed했다. exact file set 확인 후 digest를 갱신하고 모든 실패 뒤 전체 suite를 처음부터 재실행했다.
- 최종 `scripts/test.ps1`은 process-local Node.js 24.19.0에서 exit code `0`으로 통과했다. lint, mypy 48 source, backend 357/357, frontend 43/43, E2E 2/2, migration 왕복, fixture 2차 import `inserted=0`, `updated=0`, `unchanged=13`, OpenAPI drift, production build 2회, secret scan, CP2-D1 policy scan이 모두 PASS했다. standard test outbound provider request는 0이었다.
- actual credential used: `NO`. actual OAuth request: `NO`. actual market request: `NO`. D1 시작 전 승인된 anonymous canonical contract document GET만 1회 수행했으며 response는 저장하지 않았다.
- actual OAuth issuance, allowed IP, actual stocks response, actual rate-limit headers, provider timing, natural 429 `Retry-After`, edge/IP behavior는 계속 `[LIVE_UNVERIFIED]`다.
- CP2-D1 final validated implementation SHA: `7840eee70ea3d4d8be9057904501ba277e68c99a`
- CP2-D2 started: `NO`

## 현재 중지 지점 — Phase 2 CP2-D1

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2-A: `PASS`
- CP2-B: `PASS`
- CP2-B P2 hardening: `PASS`
- CP2-C: `PASS`
- CP2-C P2 cumulative-wait hardening: `PASS`
- CP2-D1: `PASS`
- CP2-D2: `NOT STARTED`
- live verification: `LIVE_UNVERIFIED`
- 실제 credential 사용: `없음`
- 실제 OAuth 요청: `없음`
- 실제 market 요청: `없음`

## 2026-08-24 — Phase 2 CP2 final integrated QA와 closeout

- 시작 branch는 `feature/phase-02-toss`, baseline/local/origin SHA는 `411749e171a717b3060973cb7b127fb94f592bab`이었고 작업트리는 clean이었다. 이 closeout에서는 application·test·migration을 수정하지 않고 문서와 final integrated QA만 수행했다.
- CP2-A의 Toss-only dependency/config/secret 경계와 account/order 금지, CP2-B의 single process token manager·memory-only lease·single-flight·monotonic expiry·exact host/method/path·401 replay 최대 1회·public raw bearer surface 부재를 코드·negative test·policy로 재검토했다.
- CP2-C의 exact 7 runtime rate group, documented/observed/effective limit, strict rate header telemetry, bounded 429/5xx retry, 누적 30초 ceiling, Reset acquire wait budget hardening과 transport error 무추측 retry 금지를 재검토했다.
- CP2-D1의 three-way opt-in, runtime provider drift gate, environment-only credential, contract/OAuth/stocks 각 최대 1회, preflight retry·refresh·replay 0, fixed safe output과 secret/body/raw-header persistence 0을 재검토했다.
- 사용자 독립 CP2-D2 one-shot의 safe fixed summary에서 provider contract drift `NO`, OpenAPI `3.1.0`, provider `1.2.14`, exact hash/origin 일치, actual OAuth와 `GET /api/v1/stocks` PASS, allowed-IP 실행 경로와 성공 응답의 Limit/Remaining/Reset header 유효성을 확인했다. closeout에서는 live API를 다시 실행하거나 credential을 요청·사용하지 않았다.
- natural 429를 고의로 유도하지 않았으므로 `Retry-After`, actual 429/5xx, production retry timing, 나머지 market endpoint와 CP3 이후 data semantics/freshness는 `[LIVE_UNVERIFIED]`로 유지했다.
- Vitest native stdout의 환경 의존 문자열 캡처를 stdout/stderr 별도 임시 파일, strict UTF-8 byte round-trip, JSON root array, exact 43개 non-empty named object와 한국어 test name 검증으로 교체한 implementation commit은 `411749e171a717b3060973cb7b127fb94f592bab`이다.
- 사용자 독립 최종 QA는 ASCII-only 경로 `C:\Users\beomoo\Documents\ChatGPT\tosstoss`, PowerShell 7.6.5, Python 3.13.15, Node 24.19.0, npm 11.17.0에서 `scripts/setup.ps1`과 `scripts/test.ps1` exit 0이었다. backend 357/357, frontend 43/43, E2E 2/2, migration, fixture idempotency, OpenAPI, production build, secret scan과 initial/final policy scan이 모두 PASS했다. D1 default와 SelfTest outbound network는 각각 0이었다.
- 이전 non-ASCII parent path에서 Python 3.13.15 + setuptools editable install의 경로 손상과 wheel build 실패가 관찰됐지만, 동일 commit의 ASCII-only clean clone에서 setup/full regression이 통과했다. 이를 Toss runtime/business defect가 아닌 `P2 DEFERRED / ENVIRONMENT CONSTRAINT`로 이월했다.
- QA 중 Codex 특정 direct process host의 Windows Python asyncio access violation 이력이 있었지만 일반 사용자 PowerShell 7.6.5, project `.venv`, exact cancellation regression과 ASCII-only clean clone 전체 회귀가 통과해 token-manager product defect로 판정하지 않았다.
- final defect 분류는 P0 0, P1 0, unresolved functional P2 0, deferred environment P2 1이다. ADR-010을 `ACCEPTED`로 변경하고 CP2를 `COMPLETE`로 닫았다.

## 현재 중지 지점 — Phase 2 CP2 closeout

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2-A: `PASS`
- CP2-B: `PASS`
- CP2-C: `PASS`
- CP2-D1: `PASS`
- CP2-D2: `PASS`
- CP2: `COMPLETE`
- CP3: `NOT STARTED`
- Phase 2: `NOT COMPLETE`

## 2026-08-24 — Phase 2 CP3-A Security Master + Current Price 계획·계약

- corrected preflight에서 `feature/phase-02-toss` local/origin SHA `6bd5d2ae9c26f02f2cd4bd75a474633a9082fa16`, remote main/merge-base `353159da45cfbe3a7f444bf476ce86fa9aece17c`, ancestry `0/18`, clean working tree를 확인했다. 로컬 main branch는 생성·변경하지 않았다.
- 현재 PowerShell 7.6.4는 previous final QA reference 7.6.5와 다르지만 repository minimum 7.4.0 이상이므로 accepted environment variance로 기록했다. Python 3.13.15, Node 24.19.0, npm 11.17.0과 ASCII-only repository path는 기준에 맞았다.
- CP3-A는 application 구현 전 문서·계약 checkpoint다. `plans/PHASE_02_CP3_A_CONTRACT.md`를 추가하고 기존 실행계획의 CP1 historical baseline, current live matrix, checkpoint 상태를 분리했다.
- `/stocks/all`은 KR/US discovery 전용, `/stocks`는 최대 200-symbol detail enrichment, `/prices`는 verified eligible security만 사용하는 역할로 제안했다. `/stocks/all`과 `/prices`는 계속 `[LIVE_UNVERIFIED]`다.
- Phase 1 Issuer의 corp_code/CIK 강제와 Toss response 부재 충돌 때문에 canonical model을 breaking 완화하지 않고 provider staging identity를 먼저 두는 ADR-012를 `PROPOSED`로 추가했다. symbol/name/ISIN 단독 자동 merge, fake regulatory ID와 unknown VERIFIED mapping을 금지했다.
- ADR-011은 observed time/date 둘 다 null인 provider 상태와 `/prices timestamp=null`을 structured missing reason으로 표현하도록 수정했지만 `PROPOSED — REVISED FOR CP3-A / AWAITING INDEPENDENT REVIEW`를 유지했다.
- current price는 strict Decimal string, nullable provider timestamp, provider currency 보존, timestamp null의 `DEGRADED/UNKNOWN`, LKG/latest pointer 보존, duplicate/revision 분리와 SQLite history 누적 금지를 계약화했다.
- collection attempt, canonical request, raw response, source version, normalized record, latest pointer와 audit event를 별도 identity로 정의했다. 기존 source-record unique 제약은 수정하지 않고 additive provider source-version table proposal로 해결했다.
- CP3-B contract foundation, CP3-C security master, CP3-D1 price offline, CP3-D2 separately approved live verification, CP3-D3 integrated closeout으로 분리했다. 각 checkpoint는 이전 승인 뒤에만 시작한다.
- application code, test, fixture, migration, dependency, runtime config, API route와 connector implementation 변경은 0이다. actual credential 사용과 actual Toss API 호출도 0이다.
- 첫 full `scripts/test.ps1`은 backend 357/357, migration, fixture idempotency, frontend 43/43, OpenAPI와 production build 2회까지 통과한 뒤 pre-existing orphaned workspace Uvicorn listener가 8000을 점유해 E2E 시작에서 exit 1이었다. 3000/8000 listener의 command line이 모두 이 repository의 Next/Uvicorn임을 확인하고 exact process tree만 종료한 뒤 두 포트가 비었음을 검증했다.
- 두 번째 full run은 backend/frontend/migration/fixture/OpenAPI/build와 E2E 2/2까지 통과한 뒤 documentation이 unstaged여서 secret scan의 index/working-tree equality gate에서 exit 1이었다. scanner 예외나 우회를 추가하지 않고 허용된 문서 7개만 stage했다.
- final staged documentation 기준 세 번째 `scripts/test.ps1`은 PowerShell 7.6.4, Python 3.13.15, Node 24.19.0, npm 11.17.0에서 exit 0이었다. exact inventory backend 357, frontend 43, E2E 2가 유지됐고 357/357, 43/43, 2/2 PASS, migration repeat/downgrade/re-upgrade, fixture 2차 import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI, production build 2회, secret scan, initial/final policy scan이 모두 PASS했다.
- Toss preflight default/SelfTest external request는 각각 0이고 default credential usage는 0이었다. test 삭제, skip/xfail, inventory 감소, assertion 완화, network 우회는 없었다.

## 현재 중지 지점 — Phase 2 CP3-A

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2: `COMPLETE`
- CP3-A: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- CP3-B: `NOT STARTED`
- ADR-011: `PROPOSED — REVISED FOR CP3-A / AWAITING INDEPENDENT REVIEW`
- ADR-012: `PROPOSED — AWAITING INDEPENDENT REVIEW`
- application implementation: `0`
- actual credential/API usage: `0`

## 2026-08-25 — Phase 2 CP3-A independent-review P1 contract fix

- 시작 preflight에서 `feature/phase-02-toss` local/origin SHA `386a0b2fe7bd18ed4b662eb2695ff85cc2a08cd3`, remote main/merge-base `353159da45cfbe3a7f444bf476ce86fa9aece17c`와 clean working tree를 확인했다.
- 첫 GPT independent review 결과는 `CHANGES REQUIRED`, P0 0/P1 2였고 CP3-B는 승인되지 않았다.
- P1-01 보완: valid·non-collision·non-quarantine `provider_security_identity_id`를 required identity로 하는 `ProviderPriceSnapshot`과 provider latest를 정의했다. `security_id`와 canonical mapping은 nullable linkage이며, verified mapping이 없어도 provider-scoped storage는 가능하지만 canonical current-price view와 issuer/company analysis 연결은 금지한다.
- P1-02 보완: observation마다 anchor priority를 재적용하지 않고 existing active identity/history continuity를 먼저 검색한다. deterministic single candidate는 immutable ID를 재사용하고 새 ISIN/listDate를 history에 추가한다. 다중 후보/active collision은 new identity·auto merge 없이 `UNRESOLVED_COLLISION`/`QUARANTINE`하며 continuity evidence 0일 때만 최초 anchor를 할당한다.
- mapping promotion은 provider identity, anchor와 기존 price/source/hash/revision history를 rekey하지 않고 nullable canonical linkage만 추가한다.
- 두 P1을 직접 검증할 P0 acceptance 7건과 false-green count/ID/hash assertion을 문서화했다. 실제 test code는 작성하지 않았다.
- ADR-010 `ACCEPTED`는 유지했다. ADR-011은 `PROPOSED — INDEPENDENT REVIEW P1-NOT-BLOCKING / AWAITING USER APPROVAL`, ADR-012는 `PROPOSED — REVISED AFTER INDEPENDENT REVIEW / AWAITING RE-REVIEW`이며 Codex가 승인하지 않았다.
- application/test/fixture/migration/dependency/runtime config/API route/connector 변경, actual credential 사용과 actual Toss API 호출은 모두 0이다.
- 허용 문서 8개를 stage한 첫 full `scripts/test.ps1`은 exit 0이었다. exact inventory backend 357/frontend 43/E2E 2를 유지했고 357/357, 43/43, 2/2 PASS, migration repeat/downgrade/re-upgrade, fixture second import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI, production build 2회, secret scan과 initial/final policy scan이 모두 PASS했다. offline Toss default/SelfTest external request와 credential usage는 0이었다.

## 현재 중지 지점 — Phase 2 CP3-A independent-review fix

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP2: `COMPLETE`
- CP3-A: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
- CP3-B: `NOT STARTED`
- automatic checkpoint progression: `PROHIBITED`

## 2026-08-25 — Phase 2 CP3-A approval and final closeout

- preflight에서 `feature/phase-02-toss` local/origin SHA `6a3e1c21160478b44824f1630c8da8e3b784fd6b`, remote main/merge-base `353159da45cfbe3a7f444bf476ce86fa9aece17c`와 clean working tree를 확인했다.
- 사용자가 제공한 GPT independent re-review 결과 `PASS WITH CLOSEOUT CONDITION`, P0 0/P1 0/P2 evidence gap 1, P1-01/P1-02 `CLOSED`를 `qa/PHASE_02_CP3_A_INDEPENDENT_QA.md`에 의미 변경 없이 별도 보존했다.
- 사용자의 명시적 결정에 따라 ADR-011과 revised ADR-012를 2026-08-25 `ACCEPTED`로 전환하고 CP3-A repository contract를 승인 상태로 정합화했다.
- P2 evidence gap은 independent QA와 Codex closeout report를 포함한 final 9-file documentation set을 먼저 완성·stage한 뒤 전체 offline regression을 수행하는 방식으로 해소했다.
- final staged set의 `scripts/test.ps1`은 exit 0이었다. exact inventory backend 357/frontend 43/E2E 2, backend 357/357, frontend 43/43, E2E 2/2, migration repeat/downgrade/re-upgrade, fixture second import `inserted=0`/`updated=0`/`unchanged=13`, OpenAPI, production build 2회, secret scan과 initial/final policy scan이 모두 PASS했다.
- offline Toss default/SelfTest external request, actual credential usage와 actual Toss API request는 모두 0이었다.
- application/test/fixture/migration/dependency/runtime config/API route/connector 변경과 CP3-B implementation은 0이다. test 삭제/skip/xfail/inventory 감소/assertion 완화/scanner 또는 network guard 우회도 0이다.

## 현재 중지 지점 — Phase 2 CP3-A approved closeout

- Phase 2: `IMPLEMENTATION IN PROGRESS`
- CP1: `PASS`
- CP2: `COMPLETE`
- CP3-A: `PASS — CONTRACT APPROVED AND CLOSED`
- ADR-011: `ACCEPTED`
- ADR-012: `ACCEPTED`
- CP3-B: `NOT STARTED`
- automatic checkpoint progression: `PROHIBITED`
