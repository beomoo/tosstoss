# Phase 1 Foundation 실행계획

- 계획 버전: 0.1.0
- 작성일: 2026-08-16
- 대상 Phase: Phase 1 — Foundation
- 현재 단계: Phase 0 문서 검토
- 구현 시작 조건: 이 계획과 qa/PHASE_00_DOCUMENT_REVIEW.md의 조건을 사용자가 승인한 뒤
- 현재 판정: CONDITIONAL PASS

## 1. 목표

실제 외부 API, 실제 계좌, 주문, OpenAI API 없이 다음 기반을 만든다.

1. Windows에서 재현 가능한 Next.js/TypeScript 프론트엔드와 FastAPI/Python 백엔드
2. 명시적으로 FIXTURE라고 표시되는 국내·미국 합성 데이터 화면
3. 버전·시간·Decimal·결측·출처·정정 상태를 엄격히 검증하는 공통 계약
4. SQLite 마이그레이션, repository 경계, 멱등 fixture import
5. localhost 전용 실행, fail-closed 설정, 구조화·마스킹 로그
6. frontend/backend 계약 일치와 자동화된 lint, typecheck, test, build, 보안 검사
7. Phase 1 자체 QA와 재현 가능한 증거

Phase 1은 후속 분석 기능을 구현하는 단계가 아니다. 정적 fixture는 계약과 화면 골격을 검증하기 위한 샘플이며 실제 분석 결과로 표현하지 않는다.

## 2. 구현 전 게이트

다음 조건이 충족되기 전에는 package, 설정, migration 또는 애플리케이션 코드를 생성하지 않는다.

| ID | 조건 | 확인 방법 |
|---|---|---|
| G-01 | 이 실행계획과 Phase 0 검토가 승인됨 | 사용자 승인 기록 |
| G-02 | 프로젝트 루트가 Git 저장소이고 문서 기준 commit이 존재함 | git rev-parse --show-toplevel, git status |
| G-03 | feature/phase-01-foundation 브랜치에서 작업함 | git branch --show-current |
| G-04 | 아래 PROPOSED ADR의 기본안이 승인됨 | DECISIONS.md에 ACCEPTED 또는 승인 기록 |
| G-05 | 실제 키가 입력되지 않음 | .env 부재 또는 안전한 placeholder만 존재, secret scan |
| G-06 | 외부 API 접근이 필요하지 않음 | 의존성 설치 외 outbound 요청 없음 |

현재 폴더는 Git 저장소가 아니다. 안전한 기본안은 현재 폴더 자체를 저장소 루트로 초기화하고 문서 묶음을 첫 commit으로 남기는 것이다. 부모 폴더 전체를 저장소로 삼지 않는다.

권장 선행 명령은 Phase 1 승인 후에만 실행한다.

~~~powershell
Set-Location -LiteralPath 'C:\Users\beomoo\Documents\ChatGPT\토스증권 자동화 매매\toss_invest_dashboard_codex_docs_v0.1'
git init -b main
git add .
git commit -m "docs: establish phase 0 baseline"
git switch -c feature/phase-01-foundation
~~~

## 3. 기술 선택

### 3.1 실행 기준

최초 확인된 로컬 환경은 PowerShell 7.6.4, Node.js 24.15.0, npm 11.12.1, Python 3.13.1, Git 2.50.1이었다. 구현 검증 중 Node.js 24.15.0의 Windows TCP 네이티브 충돌이 재현되어 검증 기준을 Node.js 24.19.0과 npm 11.17.0으로 갱신했다. uv와 gitleaks는 설치되어 있지 않다.

| 영역 | 선택 | 지원 기준 | 이유 |
|---|---|---|---|
| Shell | PowerShell Core | 7.4 이상, 검증 기준 7.6.4 | 한글·공백 경로와 Windows 프로세스 제어를 명시적으로 검증 |
| Node | Node.js | 24.16 이상 25 미만, 검증 기준 24.19.0 | 24.15 이하의 Windows TCP 네이티브 충돌을 회피하며 Next.js 16의 공식 최소 Node 20.9보다 보수적 |
| JS package manager | npm workspaces | npm 11 | 별도 전역 도구 없이 package-lock.json과 npm ci 사용 |
| Frontend | Next.js 16 App Router, React, TypeScript strict | package-lock에 정확 버전 고정 | Windows 지원, server-side API 경계, loading/error convention |
| Frontend lint/test | ESLint CLI, Vitest, Testing Library, Playwright Chromium | lockfile 고정 | Next.js 16은 next lint가 아니라 ESLint CLI를 사용; component와 E2E를 분리 |
| Python | CPython | 3.13.1 이상 3.14 미만 | 현재 py launcher로 재현 가능 |
| Python environment | venv + pip | 저장소 내부 .venv | uv가 없는 현재 환경에서 추가 전역 도구 없이 실행 |
| Backend | FastAPI, Pydantic v2 | 정확 버전 고정 | REST와 엄격한 데이터 계약 |
| Persistence | SQLAlchemy 2, Alembic, SQLite | 정확 버전 고정 | migration과 repository 경계를 검증 |
| Backend quality | Ruff, mypy, pytest, pytest-socket | 정확 버전 고정 | format/lint/type/테스트와 외부 socket 차단 |
| Secret scan | detect-secrets + 자체 bundle/policy 검사 | Python lock에 고정 | all-files 스캔, OpenAI 키 및 private key 탐지, Windows 재현 |
| Logging | Python 표준 logging 기반 JSON formatter | 자체 코드 | 불필요한 런타임 의존성 없이 schema와 redaction을 통제 |

Next.js 설치 기준: https://nextjs.org/docs/app/getting-started/installation

FastAPI 버전 고정 기준: https://fastapi.tiangolo.com/deployment/versions/

npm ci의 frozen lock 동작: https://docs.npmjs.com/cli/v11/commands/npm-ci/

Python venv Windows 실행: https://docs.python.org/3.13/library/venv.html

Alembic SQLite batch migration: https://alembic.sqlalchemy.org/en/latest/batch.html

detect-secrets all-files scan: https://github.com/Yelp/detect-secrets

### 3.2 버전 고정 정책

- package.json의 직접 의존성과 package-lock.json을 commit한다.
- 자동 검증과 setup은 npm install이 아니라 npm ci를 사용한다.
- pyproject.toml은 직접 의존성을 선언하고 requirements.lock은 모든 전이 의존성을 정확 버전과 SHA-256 hash로 고정한다.
- Python 설치는 .venv의 python.exe를 명시적으로 호출하고 PATH의 python 별칭을 사용하지 않는다.
- Phase 1 구현 중 latest, 별표 범위 또는 잠금 없는 설치를 남기지 않는다.
- Playwright는 setup에서 Chromium만 설치한다. 테스트 명령은 브라우저나 package를 다운로드하지 않는다.
- 최초 setup의 package registry/CDN 접근은 허용하지만, setup 완료 후 lint, test, build, E2E는 외부 애플리케이션 API와 package registry 없이 통과해야 한다.

## 4. Phase 1 아키텍처 경계

~~~text
Browser
  -> Next.js at 127.0.0.1:3000
       -> server-only API client
            -> FastAPI at 127.0.0.1:8000
                 -> application service
                      -> SQLite metadata repository
                      -> validated read-only fixture repository
~~~

- 브라우저 번들에는 backend URL, 시크릿 이름 또는 서버 환경 전체를 넣지 않는다.
- Next.js Server Component가 FastAPI를 호출한다. API base URL은 NEXT_PUBLIC 변수가 아닌 server-only 설정이다.
- FastAPI와 Next.js 모두 127.0.0.1에만 바인딩한다.
- 변경형 admin/settings API는 만들지 않는다.
- 외부 connector, scheduler, background job, auth/token manager는 만들지 않는다.
- 오류가 난 fixture source는 해당 카드와 Data Quality 상태만 실패로 표시하고 다른 카드와 health를 유지한다.

## 5. Phase 1 계약 결정

아래는 문서의 모호함을 안전한 기본안으로 구체화한 것이다. 계획 승인은 이 기본안의 승인으로 간주하고, 구현 시작 시 DECISIONS.md에 승인된 ADR로 반영한다.

### C-01 계약 버전

- 모든 독립 fixture 레코드와 API response envelope에 contract_version을 필수로 둔다.
- Phase 1 값은 0.1.0이다.
- 알 수 없는 major/minor는 validation error로 거부한다.
- OpenAPI snapshot과 TypeScript 생성 타입을 commit하고 재생성 diff가 0인지 검사한다.

### C-02 Issuer와 Security 분리

- Issuer는 issuer_id, legal/display name, jurisdiction, corp_code, cik을 소유한다.
- Security는 security_id, issuer_id, market, exchange, ticker, share_class, currency, cusip, isin, figi를 소유한다.
- GET /api/v1/companies/{issuer_id}/overview는 issuer 기준이며 응답에 선택된 security_id를 포함한다.
- GET /api/v1/securities는 fixture 2건의 조회만 제공한다. 검색, 관심종목, 등록은 Phase 1 비범위다.

### C-03 안정 ID와 자연키

- PriceBar, DailyMarketFlow, FinancialFact, FilingDocument, FilingSentenceChange, InstitutionHolding, InstitutionHoldingChange, ValuationScenario, Evidence, DataQualityStatus에 안정적인 내부 ID를 둔다.
- 자연키에는 데이터셋별 unique constraint를 둔다.
- 같은 ID와 같은 canonical hash 재수집은 unchanged다.
- 같은 ID와 다른 원문 hash는 덮어쓰지 않고 오류로 중단한다.
- 정정본은 새 ID를 사용하고 supersedes_id로 원본을 연결한다.

### C-04 Decimal과 JSON

- 금액, 수량, EPS, 비율, 확률, confidence는 Pydantic Decimal을 사용한다.
- JSON 표현은 지수표기 없는 canonical decimal string이다.
- 외부 JSON number 입력은 거부한다. binary float는 저장·계산·fixture에 사용하지 않는다.
- SQLite에서 정밀 수치는 canonical TEXT로 저장한다. DB round-trip 뒤 문자열 값이 정확히 같아야 한다.
- confidence와 probability는 0 이상 1 이하, scenario probability 합은 정확히 1.00이어야 한다.

### C-05 결측

- 업무 데이터의 null은 0이나 빈 문자열로 대체하지 않는다.
- 각 레코드에는 missing_reasons map을 둘 수 있고, 의미 있는 nullable 업무 필드가 null이면 해당 필드의 사유를 필수로 둔다.
- 사유 enum은 NOT_PROVIDED, NOT_APPLICABLE, UNAVAILABLE, UNRESOLVED, PARSE_ERROR, WITHHELD로 제한한다.
- UI는 null을 0으로 표시하지 않고 사유와 함께 확인 불가로 표시한다.

### C-06 시간

- instant 필드는 timezone-aware 입력만 허용하고 UTC Z 형식으로 직렬화한다.
- date-only 필드는 날짜로 유지하며 임의의 00:00 UTC를 만들지 않는다.
- PriceBar는 bar_start instant 외에 exchange_trade_date를 둔다.
- Data Quality에는 last_attempt_at, last_success_at, last_observed_at, freshness_evaluated_at을 구분한다.
- fixture freshness는 고정된 evaluated_at 기준의 명시값이며 현재 시각에 따라 테스트가 바뀌지 않는다.
- 화면은 원본 UTC와 Asia/Seoul 표시를 혼동하지 않도록 시간대 레이블을 함께 표시한다.

### C-07 상태 축 분리

- availability_status: AVAILABLE, DEGRADED, ERROR, UNAVAILABLE
- freshness_status: FRESH, STALE, EXPIRED, UNKNOWN
- finality_status: PRELIMINARY, FINAL, REVISED, UNKNOWN
- revision_status: ORIGINAL, AMENDED, SUPERSEDED, MERGED
- job status와 HTTP health는 위 상태와 별도다.
- source가 ERROR여도 마지막 정상 레코드는 삭제하지 않고 stale/last-success 정보를 함께 보여준다.

### C-08 출처와 hash

- SourceRecord에는 raw_content_hash를 sha256:<64 lowercase hex> 형식으로 둔다.
- 정규화 레코드에는 canonical JSON의 normalized_content_hash를 둔다.
- canonical JSON 규칙은 UTF-8, key 정렬, 공백 없음, Decimal string 보존으로 고정한다.
- raw_storage_ref는 opaque 내부 참조이며 API나 UI에 로컬 절대경로를 노출하지 않는다.
- source_locator는 https만 클릭 가능하게 하고 fixture://는 텍스트로만 표시한다.
- javascript:, data:, file: URL은 거부한다.

### C-09 Fixture 진실성

- 모든 응답 envelope와 /api/v1/system/status에 data_mode: FIXTURE를 둔다.
- 합성 회사명과 존재하지 않는 테스트 ticker를 사용하며 실제 기업 수치처럼 보이는 fixture를 만들지 않는다.
- 화면 상단에 항상 보이는 FIXTURE / 실제 투자 데이터 아님 배너를 둔다.
- 정적 filing change, valuation, institutional change, analysis packet은 SAMPLE_RESULT로 표시한다.

### C-10 가치평가와 공시 변화

- ValuationScenario의 assumption_source canonical 값은 USER_ASSUMPTION이다. docs/04 예시의 USER는 사용하지 않는다.
- Phase 1 valuation fixture는 PER 한 종류의 정적 샘플만 검증하고 계산 엔진은 만들지 않는다.
- FilingSentenceChange는 primary_change_type과 change_types 배열을 사용해 복수 태그를 보존한다.
- review_status와 human_review_required를 둘 다 명시하되 실제 review workflow는 만들지 않는다.

### C-11 Evidence 분류

- evidence_basis: DIRECT_SOURCE, CALCULATED, STRUCTURAL_INFERENCE
- verification_status: LATEST_VERIFIED, UNCONFIRMED, NOT_CHECKED
- freshness와 verification을 evidence type 하나에 섞지 않는다.
- Hypothesis, InvalidationCondition, ScenarioProbabilityChange의 DB 테이블과 규칙 엔진은 만들지 않고 analysis packet의 versioned extensions 위치만 둔다.

### C-12 API와 오류 envelope

Phase 1 endpoint를 다음으로 고정한다.

| Endpoint | 정상 결과 | 실패 |
|---|---|---|
| GET /health | liveness 200, service/version/data_mode | 예외 정보 없음 |
| GET /api/v1/system/status | 허용 목록 상태, DB revision, fixture version | 503 구조화 오류 |
| GET /api/v1/securities | 합성 security 2건 | 빈 배열 200 |
| GET /api/v1/companies/{issuer_id}/overview | 합성 overview aggregate | 미존재 404 |
| GET /api/v1/companies/{issuer_id}/data-quality | source별 상태 | 미존재 404 |
| GET /api/v1/sample/analysis-packet | 정적 fixture packet | fixture 누락 503 |

Error envelope는 contract_version, error.code, error.message, request_id만 노출한다. traceback, 파일 경로, 환경변수, raw payload, Authorization을 반환하지 않는다.

## 6. 저장 범위

Phase 1은 SQLite와 저장 인터페이스까지만 구현한다.

### SQLite에 저장

- schema revision
- issuers
- securities
- source_records
- data_quality_statuses
- fixture_import_runs와 manifest digest

### 검증된 read-only JSON fixture repository로 제공

- price bars
- domestic market flows
- financial facts
- institution managers/holdings/changes
- filing documents/sentence changes
- valuation scenarios
- evidence
- analysis packet sample

Parquet와 DuckDB 물리 저장은 Phase 2 이후로 이연한다. Phase 1에는 AnalyticsRepository protocol과 fixture adapter만 둔다. 가격·수급·재무·13F 시계열을 편의상 SQLite에 저장하지 않는다.

## 7. 구현 체크포인트

### Checkpoint 0 — 승인·Git·기준선

작업:

- 이 계획 승인 확인
- 현재 프로젝트 폴더에 Git 초기화
- 문서 기준 commit 생성
- feature/phase-01-foundation 브랜치 생성
- 승인된 PROPOSED ADR을 DECISIONS.md에 반영

검증:

~~~powershell
git rev-parse --show-toplevel
git branch --show-current
git status --short
~~~

중단 조건: 경로가 현재 프로젝트 폴더가 아니거나 기존 Git 이력과 충돌하면 구현을 시작하지 않는다.

### Checkpoint 1 — 재현 가능한 scaffold

작업:

- root npm workspace와 Python pyproject/lock 생성
- .gitignore, safe .env.example, version files 생성
- scripts/common.ps1, setup.ps1 작성
- setup은 도구 버전 검증, .venv 생성, hash-pinned Python 설치, npm ci, Playwright Chromium 설치를 수행
- 모든 스크립트는 $PSScriptRoot와 LiteralPath를 사용하고 외부 명령의 exit code를 전파

검증:

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
~~~

기대: 두 실행 모두 성공하고 시스템 전역 package를 변경하지 않는다.

### Checkpoint 2 — 계약과 fixture

작업:

- C-01부터 C-12까지 Pydantic 모델·enum·validator 구현
- 국내 합성 issuer/security 1개, 미국 합성 issuer/security 1개 fixture 작성
- manifest, raw fixture, normalized fixture, known SHA-256 작성
- OpenAPI snapshot과 TypeScript 타입 생성 경로 작성

검증:

- 모든 정상 fixture validation PASS
- invalid fixture가 예상 error code로 FAIL
- Decimal, UTC, null, enum, ID/FK, hash, revision 테스트 PASS
- TypeScript strict typecheck PASS

### Checkpoint 3 — SQLite migration과 repository

작업:

- SQLAlchemy sync engine와 명시적 transaction
- Alembic 최초 migration
- repository protocols와 SQLite/fixture adapters
- fixture importer

검증:

- 임시 빈 DB upgrade head 성공
- 같은 DB에 upgrade head 재실행 성공, schema fingerprint 동일
- 임시 DB downgrade base 후 재upgrade 성공
- 동일 manifest 두 번 import 후 두 번째 결과 inserted=0, updated=0, unchanged=N
- row count, PK set, canonical digest 동일
- invalid fixture import는 전체 rollback
- 정정 레코드가 원본을 덮어쓰지 않음

### Checkpoint 4 — FastAPI

작업:

- config fail-closed
- localhost/trusted host/exact CORS
- request ID, JSON log, redaction, safe exception handler
- C-12 endpoint 구현
- startup에서 migration revision과 fixture manifest 확인

검증:

- endpoint schema와 HTTP status
- unknown issuer 404
- repository failure 503
- source ERROR가 다른 endpoint를 막지 않음
- 위험 flag true, wildcard host/origin, naive timestamp를 거부
- canary secret가 response/log/traceback에 없음

### Checkpoint 5 — Next.js fixture UI

작업:

- server-only FastAPI client
- App shell과 disabled future navigation
- Company fixture page
- Data Quality fixture page
- health 상태
- loading, empty, error, not-found 화면
- FIXTURE 배너와 텍스트 기반 상태 표시
- system font, CSP, URL scheme validation

검증:

- component tests: null, timezone, Decimal, status, disabled navigation, error/empty/loading
- 악성 HTML은 text로 escape되고 javascript: 링크는 생성되지 않음
- 브라우저 bundle에 backend URL, sentinel secret, 민감 env 이름이 없음
- Playwright smoke와 screenshot 생성

### Checkpoint 6 — 통합 보안·범위 검사

작업:

- scripts/lint.ps1, typecheck.ps1, build.ps1, test.ps1
- migrate/import/e2e/secret-scan/policy-scan scripts
- 외부 socket 차단
- skip/todo/xfail 금지 검사
- 주문·계좌·OpenAI·external connector dependency/route 부재 검사

검증:

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\lint.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\typecheck.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\secret-scan.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1
~~~

모든 명령의 기대 exit code는 0이다. test.ps1은 설치나 다운로드를 수행하지 않는다.

### Checkpoint 7 — QA와 종료

작업:

- qa/PHASE_01_SELF_QA.md 작성
- 샘플 API JSON, migration/import 로그, Playwright 결과와 screenshot 보존
- STATUS.md, CHANGELOG.md 갱신
- 실제 미완료 항목만 KNOWN_ISSUES.md 갱신
- git diff와 secret scan을 마지막으로 재검증

검증:

- P0=0, P1=0
- P2는 수정 또는 사용자 승인 이월
- 모든 필수 artifact 존재
- 실제 실행한 commit SHA와 명령 결과 기록
- fixture를 실제 원문으로 기재하지 않고 실제 원문 항목은 N/A — Phase 1 비범위로 기록

## 8. 생성·수정 파일

아래는 Phase 1에서 계획된 파일이다. 빈 미래 디렉터리나 사용하지 않는 connector scaffold는 만들지 않는다.

### 8.1 루트

생성:

~~~text
.editorconfig
.env.example
.gitignore
.node-version
.python-version
README.md
package.json
package-lock.json
pyproject.toml
requirements.lock
alembic.ini
contracts/openapi.json
~~~

### 8.2 Backend

생성:

~~~text
services/api/src/toss_dashboard_api/__init__.py
services/api/src/toss_dashboard_api/main.py
services/api/src/toss_dashboard_api/config.py
services/api/src/toss_dashboard_api/logging_config.py
services/api/src/toss_dashboard_api/errors.py
services/api/src/toss_dashboard_api/middleware.py
services/api/src/toss_dashboard_api/contracts/base.py
services/api/src/toss_dashboard_api/contracts/enums.py
services/api/src/toss_dashboard_api/contracts/issuer.py
services/api/src/toss_dashboard_api/contracts/security.py
services/api/src/toss_dashboard_api/contracts/source.py
services/api/src/toss_dashboard_api/contracts/market.py
services/api/src/toss_dashboard_api/contracts/financial.py
services/api/src/toss_dashboard_api/contracts/institution.py
services/api/src/toss_dashboard_api/contracts/filing.py
services/api/src/toss_dashboard_api/contracts/valuation.py
services/api/src/toss_dashboard_api/contracts/evidence.py
services/api/src/toss_dashboard_api/contracts/quality.py
services/api/src/toss_dashboard_api/contracts/packet.py
services/api/src/toss_dashboard_api/contracts/responses.py
services/api/src/toss_dashboard_api/domain/overview.py
services/api/src/toss_dashboard_api/repositories/protocols.py
services/api/src/toss_dashboard_api/repositories/sqlite.py
services/api/src/toss_dashboard_api/repositories/fixture.py
services/api/src/toss_dashboard_api/storage/database.py
services/api/src/toss_dashboard_api/storage/models.py
services/api/src/toss_dashboard_api/storage/decimal_text.py
services/api/src/toss_dashboard_api/fixtures/importer.py
services/api/src/toss_dashboard_api/routes/health.py
services/api/src/toss_dashboard_api/routes/system.py
services/api/src/toss_dashboard_api/routes/securities.py
services/api/src/toss_dashboard_api/routes/companies.py
services/api/src/toss_dashboard_api/routes/sample.py
services/api/alembic/env.py
services/api/alembic/script.py.mako
services/api/alembic/versions/0001_phase_01_foundation.py
~~~

### 8.3 Frontend

생성:

~~~text
apps/web/package.json
apps/web/next.config.ts
apps/web/tsconfig.json
apps/web/eslint.config.mjs
apps/web/vitest.config.ts
apps/web/vitest.setup.ts
apps/web/playwright.config.ts
apps/web/src/app/globals.css
apps/web/src/app/layout.tsx
apps/web/src/app/page.tsx
apps/web/src/app/loading.tsx
apps/web/src/app/error.tsx
apps/web/src/app/not-found.tsx
apps/web/src/app/company/[issuerId]/page.tsx
apps/web/src/app/company/[issuerId]/loading.tsx
apps/web/src/app/company/[issuerId]/error.tsx
apps/web/src/app/data-quality/page.tsx
apps/web/src/components/AppShell.tsx
apps/web/src/components/FixtureBanner.tsx
apps/web/src/components/BackendStatus.tsx
apps/web/src/components/DataField.tsx
apps/web/src/components/StatusBadge.tsx
apps/web/src/components/StatePanel.tsx
apps/web/src/components/CompanyOverview.tsx
apps/web/src/components/DataQualityGrid.tsx
apps/web/src/lib/api.server.ts
apps/web/src/lib/format.ts
apps/web/src/lib/safe-url.ts
apps/web/src/types/api.generated.ts
apps/web/src/components/FixtureBanner.test.tsx
apps/web/src/components/DataField.test.tsx
apps/web/src/components/StatePanel.test.tsx
apps/web/src/components/CompanyOverview.test.tsx
apps/web/src/components/DataQualityGrid.test.tsx
apps/web/src/lib/format.test.ts
apps/web/src/lib/safe-url.test.ts
apps/web/tests/e2e/phase-01.spec.ts
~~~

### 8.4 Fixtures

생성:

~~~text
fixtures/phase_01/manifest.json
fixtures/phase_01/raw/kr_filing_original.fixture.json
fixtures/phase_01/raw/kr_filing_amended.fixture.json
fixtures/phase_01/raw/us_holding.fixture.json
fixtures/phase_01/issuers.json
fixtures/phase_01/securities.json
fixtures/phase_01/source_records.json
fixtures/phase_01/price_bars.json
fixtures/phase_01/daily_market_flows.json
fixtures/phase_01/financial_facts.json
fixtures/phase_01/institution_managers.json
fixtures/phase_01/institution_holdings.json
fixtures/phase_01/institution_holding_changes.json
fixtures/phase_01/filing_documents.json
fixtures/phase_01/filing_sentence_changes.json
fixtures/phase_01/valuation_scenarios.json
fixtures/phase_01/evidence.json
fixtures/phase_01/data_quality_statuses.json
fixtures/phase_01/analysis_packet.json
tests/fixtures/invalid/decimal_number.json
tests/fixtures/invalid/naive_timestamp.json
tests/fixtures/invalid/missing_reason_absent.json
tests/fixtures/invalid/unknown_enum.json
tests/fixtures/invalid/hash_mismatch.json
tests/fixtures/invalid/revision_cycle.json
~~~

### 8.5 Backend tests

생성:

~~~text
tests/backend/conftest.py
tests/backend/test_contract_required_fields.py
tests/backend/test_contract_decimal.py
tests/backend/test_contract_time.py
tests/backend/test_contract_null_enum.py
tests/backend/test_contract_ids_hashes.py
tests/backend/test_contract_roundtrip.py
tests/backend/test_settings_security.py
tests/backend/test_logging_redaction.py
tests/backend/test_migrations.py
tests/backend/test_fixture_import.py
tests/backend/test_repositories.py
tests/backend/test_api_health_status.py
tests/backend/test_api_companies.py
tests/backend/test_api_data_quality.py
tests/backend/test_api_analysis_packet.py
tests/backend/test_error_isolation.py
tests/backend/test_openapi_snapshot.py
tests/backend/test_no_external_network.py
~~~

### 8.6 Scripts와 QA

생성:

~~~text
scripts/common.ps1
scripts/setup.ps1
scripts/dev.ps1
scripts/lint.ps1
scripts/typecheck.ps1
scripts/build.ps1
scripts/test.ps1
scripts/migrate.ps1
scripts/import-fixtures.ps1
scripts/export-openapi.ps1
scripts/e2e.ps1
scripts/secret-scan.ps1
scripts/policy-scan.ps1
qa/PHASE_01_SELF_QA.md
qa/evidence/phase_01/sample-health.json
qa/evidence/phase_01/sample-company-overview.json
qa/evidence/phase_01/sample-data-quality.json
qa/evidence/phase_01/sample-analysis-packet.json
qa/evidence/phase_01/company.png
qa/evidence/phase_01/data-quality.png
~~~

수정:

~~~text
DECISIONS.md
STATUS.md
CHANGELOG.md
KNOWN_ISSUES.md   # 실제 잔여 문제가 있을 때만
~~~

수정하지 않음:

~~~text
docs/00_MASTER_IMPLEMENTATION_PLAN.md
docs/01_PRODUCT_REQUIREMENTS.md
docs/02_ARCHITECTURE.md
docs/03_DATA_SOURCES_AND_FRESHNESS.md
docs/04_DATA_CONTRACTS.md
docs/05_INSTITUTIONAL_FLOW_SPEC.md
docs/06_VALUATION_SPEC.md
docs/07_FILING_DIFF_SPEC.md
docs/08_MACRO_COMPANY_IMPACT_SPEC.md
docs/09_ASSETSQUARE_INTERFACE_SPEC.md
docs/10_SECURITY_AND_OPERATIONS.md
docs/11_ACCEPTANCE_TESTS.md
docs/12_CODEX_WORKFLOW.md
docs/13_UI_AND_DASHBOARD_SPEC.md
docs/14_NEWS_AND_EVENT_SPEC.md
PACKAGE_MANIFEST.json
~~~

PACKAGE_MANIFEST.json은 전달받은 0.1 문서 묶음의 무결성 목록이므로 동적 프로젝트 파일 목록으로 재해석하지 않는다.

## 9. Fixture 구체안

| Fixture | 최소 내용 | 자동 확인 |
|---|---|---|
| 국내 issuer/security | 합성 회사, KRW, COMMON, corp_code는 합성값, cik null | issuer/security 분리, null 사유 |
| 미국 issuer/security | 합성 회사, USD, COMMON, cik 합성값, corp_code null | 시장·통화·식별자 혼합 방지 |
| PriceBar | 각 security 일봉 2건 | OHLC 불변식, Decimal string, trade date |
| DailyMarketFlow | 국내 participant 3종, 하나의 null | participant enum, null≠0 |
| FinancialFact | 매출/EPS, 큰 정수와 소수 | unit/currency, DB/API round-trip |
| InstitutionHolding | 미국 holding original과 change | quantity/value 분리, period, mapping |
| Filing | original과 amended | 원본 보존, supersedes 연결, cycle 금지 |
| FilingSentenceChange | NUMBER_CHANGED + TONE_DOWN 복수 태그 | primary/list 일치, static sample 표시 |
| ValuationScenario | BEAR/BASE/BULL PER-only | USER_ASSUMPTION, 합 1.00, 엔진 아님 |
| Data Quality | AVAILABLE+FRESH, DEGRADED+STALE, ERROR, UNAVAILABLE | 상태 축 분리, last-success 유지 |
| Analysis packet | evidence, source manifest, unconfirmed, extensions | version/data mode, 규칙 엔진 없음 |

실제 기업명, 실제 종목코드, 실제 기사, 추측한 Toss/OpenDART/SEC 응답 구조는 fixture에 넣지 않는다.

## 10. 계약 테스트 사례

### 10.1 정상 사례

1. timezone offset이 있는 입력을 UTC Z로 정규화한다.
2. 999999999999999999999999.000100을 JSON → Pydantic → SQLite TEXT → API → JSON으로 왕복해 동일 문자열을 얻는다.
3. null과 missing_reasons가 함께 있을 때 그대로 직렬화한다.
4. 정정 SourceRecord가 원본과 함께 존재하고 supersedes_id를 역참조할 수 있다.
5. raw bytes와 canonical normalized JSON의 known SHA-256가 manifest와 일치한다.
6. 모든 source_record_id와 input_data_ids가 실제 fixture ID를 참조한다.
7. contract_version 0.1.0의 dump/load가 동일하다.
8. Data Quality ERROR에서 last_success_at과 마지막 정상 데이터가 보존된다.

### 10.2 거부 사례

1. 필수 ID가 없음
2. timestamp에 timezone이 없음
3. Decimal 필드가 JSON number 또는 NaN/Infinity임
4. null인데 missing reason이 없음
5. 정의되지 않은 enum 또는 contract version
6. probability가 범위를 벗어나거나 합이 1.00이 아님
7. OHLC에서 high가 low보다 작음
8. 음수 volume 또는 records count
9. period_start가 period_end보다 늦음
10. hash 형식 또는 실제 digest 불일치
11. supersedes cycle 또는 자기 참조
12. 존재하지 않는 source/issuer/security ID 참조
13. javascript:, data:, file: locator
14. 같은 안정 ID에 다른 hash를 덮어쓰려는 import

## 11. Windows 실행 계약

### 최초 setup

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
~~~

### 개발 서버

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
Invoke-RestMethod http://127.0.0.1:8000/health
~~~

dev.ps1은 두 서버를 로컬 주소에만 바인딩하고 종료 시 자신이 만든 자식 프로세스만 정리한다. 포트 충돌 시 기존 프로세스를 종료하지 않고 오류를 반환한다.

### 개별 검증

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\migrate.ps1 -Action Test
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\import-fixtures.ps1 -VerifyIdempotency
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\lint.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\typecheck.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\secret-scan.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\policy-scan.ps1
~~~

### 전체 검증

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1
~~~

test.ps1은 다음 순서의 모든 실패를 즉시 non-zero로 전파한다.

1. backend Ruff format/check
2. backend mypy
3. backend unit/contract/integration
4. migration repeat/downgrade/re-upgrade
5. fixture import repeat/rollback
6. frontend ESLint
7. frontend TypeScript
8. frontend Vitest
9. OpenAPI snapshot/type generation drift
10. Next production build
11. Playwright smoke
12. source/artifact/.next bundle secret scan
13. prohibited scope and skip/todo/xfail scan

## 12. 보안 검증

- LOCAL_ONLY=true
- TRADING_ENABLED=false
- DRY_RUN=true
- OPENAI_API_ENABLED=false
- ALLOW_ACCOUNT_ENDPOINTS=false

위 값은 환경변수가 없어도 코드 기본값으로 유지된다. LOCAL_ONLY=false, TRADING_ENABLED=true, DRY_RUN=false, OPENAI_API_ENABLED=true 또는 ALLOW_ACCOUNT_ENDPOINTS=true이면 Phase 1 앱은 startup을 실패한다.

Secret scan은 다음을 모두 검사한다.

- Git tracked/untracked 프로젝트 파일
- fixtures와 QA JSON
- 구조화 로그 test artifact
- .next/static 브라우저 bundle
- private key, bearer token, 알려진 provider prefix, 고엔트로피 문자열
- .env가 ignore되고 Git에 추적되지 않음
- runtime sentinel secret가 API, log, traceback, HTML, JS bundle에 없음

node_modules, .venv, .git, Playwright browser cache만 제외한다. false positive 예외는 파일과 줄, 사유가 좁게 기록되지 않으면 허용하지 않는다.

Policy scan은 다음 부재를 검사한다.

- openai package/import/call
- Toss/OpenDART/SEC/news/macro HTTP connector
- order, trade execution, account endpoint/route
- wildcard CORS와 0.0.0.0 bind
- frontend의 민감 env 접근
- 테스트 skip, todo, xfail
- remote font, analytics, telemetry

Policy scan의 대상은 package/lock file, services/api, apps/web, tests, scripts로 제한한다. 미래 요구를 설명하기 위해 금지 용어가 정상적으로 존재하는 docs, plans, prompts, qa 문서는 정적 금지어 검색 대상에서 제외한다. skip/todo/xfail 검사는 실제 test source와 test configuration에만 적용한다.

## 13. 실패·롤백·멱등성

### 실패 처리

- setup 실패는 기존 사용자 파일을 삭제하지 않는다. 재실행 가능해야 한다.
- migration/import/test는 임시 디렉터리와 임시 SQLite DB를 사용한다.
- fixture validation 실패는 transaction 전체를 rollback하고 이전 digest를 유지한다.
- API repository 실패는 safe 503과 source status로 격리한다.
- 테스트 실패를 skip, xfail, 삭제 또는 조건부 우회로 숨기지 않는다.

### 롤백

- 코드 롤백은 feature branch의 checkpoint commit을 git revert한다. destructive reset을 사용하지 않는다.
- migration downgrade는 disposable test DB에서 반드시 검증한다.
- 실제 사용자 DB가 없는 Phase 1에서는 data reset/delete script를 만들지 않는다.
- setup은 시스템 전역 Node/Python package를 수정하지 않고 .venv와 node_modules만 사용한다.
- backup.ps1과 restore-test.ps1은 읽기 전용 v1.0 전 요구이며 Phase 1에서 구현하지 않는다.

### 멱등성

- setup 두 번 실행 가능
- Alembic upgrade head 두 번 후 schema fingerprint 동일
- fixture import 두 번 후 두 번째 inserted=0, updated=0, unchanged=N
- OpenAPI와 generated TypeScript 재생성 diff 0
- 같은 raw ID/hash는 unchanged, 다른 hash는 overwrite 금지
- 정정은 append와 linkage만 수행

## 14. 명시적 비범위

- Toss, OpenDART, SEC EDGAR, 뉴스, 매크로의 실제 HTTP 호출
- connector 인증, token manager, rate limit, retry
- 계좌 조회, settings/admin 변경 API
- 주문, 모의주문, 자동매매, 주문용 interface
- OpenAI API, OpenAI SDK, 자동 prompt 실행
- 유료 API 또는 유료 서비스
- 실제 valuation 계산, DCF, reverse valuation
- 실제 filing diff/NLP/semantic similarity
- 실제 13F parser, 기관 합의, 패시브·액티브 추정
- 실제 뉴스 이벤트 dedupe 또는 기사 전문 저장
- 실제 매크로 영향·AssetSquare 규칙 엔진
- scheduler와 background collection
- DuckDB/Parquet 물리 저장
- Docker, cloud, LAN/공개 배포, CI/CD
- production backup/restore, 자동 삭제·정리
- 관심종목, 알림, 포트폴리오, 캘린더, 메모·태그
- chart indicator, 상대강도, 지지·저항 계산
- 모바일 최적화와 전체 제품 화면 구현

미래 메뉴는 필요할 때 disabled placeholder로만 표시하고 구현 완료처럼 보이게 하지 않는다.

## 15. 자동 검증 가능한 완료 기준

| ID | 완료 기준 | 증거 |
|---|---|---|
| D-01 | Windows setup 두 번 PASS | setup log |
| D-02 | frontend/backend가 127.0.0.1에서 실행 | Invoke-RestMethod, Playwright |
| D-03 | /health와 5개 Phase 1 API 계약 PASS | pytest integration, sample JSON |
| D-04 | 합성 Company/Data Quality 화면과 FIXTURE 배너 | Playwright screenshot |
| D-05 | loading/empty/error/not-found가 결정적으로 검증됨 | Vitest/Playwright |
| D-06 | Pydantic contract 정상·실패 matrix PASS | pytest |
| D-07 | Decimal/UTC/null/hash/ID/revision 왕복 PASS | pytest |
| D-08 | migration repeat/downgrade/re-upgrade PASS | migration log |
| D-09 | import repeat와 failure rollback PASS | importer log와 digest |
| D-10 | structured log schema와 redaction PASS | captured log test |
| D-11 | frontend lint/type/unit/build/E2E PASS | test log |
| D-12 | backend format/lint/type/unit/integration PASS | test log |
| D-13 | source/artifact/bundle secret scan PASS | scan report |
| D-14 | 주문·계좌·OpenAI·외부 connector가 없음 | policy scan |
| D-15 | setup 후 test가 package download와 외부 API 없이 PASS | socket guard와 test log |
| D-16 | skip/todo/xfail 0개 | policy scan |
| D-17 | qa/PHASE_01_SELF_QA.md와 증거 파일 존재 | file check |
| D-18 | STATUS/CHANGELOG와 실제 commit SHA 일치 | git diff, QA |
| D-19 | P0=0, P1=0, P2 수정 또는 승인 이월 | QA matrix |

하나라도 필수 항목이 미실행되거나 실패하면 완료로 선언하지 않는다. 필수 미완료는 PARTIAL 또는 BLOCKED 구현 상태이고 QA 판정은 FAIL이다. 승인된 P2 이월만 CONDITIONAL PASS가 가능하다.

## 16. OPEN QUESTION과 기본안

### OQ-01 — 계약·저장 ADR 승인

사용자 승인이 필요한 항목은 C-01부터 C-12와 SQLite-only Phase 1 경계다. 안전한 기본안은 본 계획 그대로이며, 이 계획 승인으로 채택된 것으로 본다.

### OQ-02 — Git 초기화

현재 폴더에는 Git 저장소가 없다. 안전한 기본안은 현재 프로젝트 폴더에서 main을 초기화하고 문서 기준 commit 후 feature/phase-01-foundation을 만드는 것이다. 기존 원격 저장소가 따로 있다는 사용자 정보가 들어오면 초기화 전에 중단하고 그 저장소를 확인한다.

## 17. 최종 판정

Phase 1은 구현 가능하다. 다만 계약 기본안 승인과 Git 기준선 확보가 선행되어야 한다.

**CONDITIONAL PASS**
