# Phase 0 문서 독립 검토

- 검토일: 2026-08-16
- 검토 대상: 문서 패키지 0.1.0
- 현재 Phase: Phase 0 — 문서 검토 및 Phase 1 실행계획
- 검토 성격: 읽기 전용 사양 검토
- 애플리케이션 코드 변경: 없음
- 판정: CONDITIONAL PASS

## 1. 검토 증거

다음을 모두 읽고 상호 대조했다.

~~~text
README_START_HERE.md
AGENTS.md
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
plans/PHASE_01_FOUNDATION_BRIEF.md
STATUS.md
DECISIONS.md
KNOWN_ISSUES.md
prompts/01_PHASE_01_GOAL_PROMPT.md
prompts/02_PHASE_01_INDEPENDENT_REVIEW_PROMPT.md
templates/PHASE_QA_TEMPLATE.md
~~~

첨부된 C:\Users\beomoo\Downloads\00_PHASE_00_PLAN_PROMPT.md와 저장소의 prompts/00_PHASE_00_PLAN_PROMPT.md는 다음 SHA-256로 완전히 동일하다.

~~~text
FE79C17A42E7A377658F5891C99F7777064A574257434701F4E8EF96D9A9F8EC
~~~

따라서 첨부 문서의 지시를 저장소의 Phase 0 지시와 동일한 것으로 검증했다.

환경 확인 결과:

| 항목 | 결과 |
|---|---|
| PowerShell | 7.6.4 |
| Node.js | 24.15.0 |
| npm | 11.12.1 |
| Python launcher | Python 3.13.1 |
| Git | 2.50.1.windows.1 |
| uv | 설치되지 않음 |
| gitleaks | 설치되지 않음 |
| detect-secrets | 설치되지 않음 |
| Git 저장소 | 아님 |

현재 폴더에는 애플리케이션 코드, package file, DB migration이 없고 문서만 있다. 첨부 지시에 맞게 이번 단계에서는 plans/PHASE_01_EXECUTION_PLAN.md와 이 문서만 생성했다.

## 2. 요약 판정

문서의 제품 방향, 읽기 전용 원칙, 외부 API 단계 분리, 시크릿 금지, 정정 이력 보존, fixture 우선 검증은 일관되고 구현 가능하다. 즉시 P0로 분류할 실제 시크릿 노출, 주문 경로, 원본 훼손 코드는 현재 존재하지 않는다.

다만 Phase 1을 구현자가 임의 해석 없이 시작하기에는 다음 핵심 규칙이 불완전하다.

1. 계약 버전과 호환성
2. Issuer–Security 식별 경계와 API path ID
3. normalized record의 안정 ID와 원문·정규화 hash
4. Decimal, null, 날짜·시각의 canonical 규칙
5. freshness와 availability/error 상태 분리
6. company overview, system status, analysis packet, error response 계약
7. SQLite와 Parquet/DuckDB의 Phase 1 물리 저장 범위
8. fixture가 실제 데이터처럼 보이지 않게 하는 자동 기준
9. 현재 폴더의 Git 기준선 부재

plans/PHASE_01_EXECUTION_PLAN.md가 이 항목들의 안전한 기본안을 고정했다. 그 기본안 승인과 Git 기준선 확보를 조건으로 Phase 1을 시작할 수 있다.

## 3. 잘 정의된 부분

| ID | 항목 | 근거 |
|---|---|---|
| OK-01 | 실제 주문·자동매매는 현재 범위가 아님 | README, AGENTS, Master, Product Requirements, Security |
| OK-02 | Phase 1 외부 API 연결 금지 | Master Phase 1, Foundation Brief |
| OK-03 | 누락값을 0으로 대체하지 않음 | AGENTS, Data Contracts, Acceptance |
| OK-04 | 원문·정규화·분석 계층 분리 | Architecture |
| OK-05 | 공시 정정과 13F 수정 이력 보존 | Data Sources, Institutional Flow |
| OK-06 | 13F를 실시간 거래 데이터로 표현하지 않음 | Product Requirements, Institutional Flow |
| OK-07 | 실제 수치와 구조적 추론 분리 | Master, AssetSquare |
| OK-08 | localhost와 시크릿 서버 전용 원칙 | Security and Operations |
| OK-09 | Phase별 plan, goal, 독립 리뷰 gate | Codex Workflow |
| OK-10 | Phase 1 정적 fixture와 실제 엔진 비범위 구분 | Foundation Brief |

## 4. Phase 1 직접 영향 발견사항

### DR-001 — 계약 버전 요구가 예시에 없음

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: docs/04_DATA_CONTRACTS.md §1은 계약 버전을 포함하라고 하지만 §§2–15 예시에는 버전 필드가 없다. §16은 버전 호환 테스트를 요구하나 호환 규칙이 없다.
- 영향: Pydantic, fixture, API, TypeScript의 호환 판정을 자동화할 수 없다.
- 기본안: 모든 독립 record와 response envelope에 contract_version 0.1.0을 필수로 두고 지원하지 않는 버전을 거부한다.
- 검증: 누락·지원·미지원 버전 test, OpenAPI snapshot drift test.

### DR-002 — Issuer/Company 계약과 API ID가 없음

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: docs/04의 여러 계약이 issuer_id를 참조하지만 Issuer 모델이 없다. docs/02 §6의 /companies/{id}에서 id 의미가 정의되지 않았다. corp_code와 CIK가 SecurityMaster 예시에 섞여 있다.
- 영향: 동일 발행사의 복수 클래스, ADR·본주, issuer와 security의 데이터가 혼동될 수 있다.
- 기본안: 최소 Issuer 계약을 추가하고 issuer 식별자와 security 식별자를 분리한다. company route는 issuer_id를 사용하고 응답에 security_id를 함께 둔다.
- 검증: 동일 issuer의 복수 security 확장 가능성, 잘못된 issuer/security 결합 거부.

### DR-003 — 정규화 레코드의 안정 ID가 부족함

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: Master §3.4는 입력 데이터 ID를 요구하고 ValuationScenario는 fact_..., price_...를 참조하지만 PriceBar, FinancialFact 등에는 자체 ID가 없다.
- 영향: 입력 추적, 멱등 upsert, 수정 이력, FK validation이 불가능하다.
- 기본안: Phase 1에 쓰는 모든 record에 안정 ID와 natural unique key를 둔다.
- 검증: FK 무결성, 동일 ID·동일 hash unchanged, 동일 ID·다른 hash 거부.

### DR-004 — Decimal JSON 표현이 문서 사이에서 다름

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: docs/04는 금액·수량·비율에 Decimal을 요구하고 예시는 문자열이다. docs/07, docs/08, docs/14의 confidence 예시는 JSON number다.
- 영향: binary float가 들어오거나 frontend/backend가 다른 타입을 사용할 수 있다.
- 기본안: 금액·수량·EPS·비율·확률·confidence를 canonical decimal string으로 통일하고 JSON number 입력을 거부한다.
- 검증: 큰 수·음수·소수 정밀도와 JSON→DB→API round-trip.

### DR-005 — SQLite 정밀 저장 규칙이 없음

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: docs/04 §1은 Decimal 또는 정밀 numeric을 요구하고 Architecture는 SQLite를 지정한다. SQLite NUMERIC affinity 자체는 임의 정밀 Decimal 보존을 보장하지 않는다.
- 영향: REAL 변환으로 금액·수량이 훼손될 수 있다.
- 기본안: Phase 1 SQLite exact numeric은 canonical TEXT로 저장하고 Pydantic Decimal로만 계산한다.
- 검증: 24자리 이상 수와 trailing zero 정책을 포함한 DB 왕복.

### DR-006 — null과 missing_reason의 규범이 약함

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: docs/04 §1은 missing_reason을 함께 둘 수 있다고만 한다. 각 계약에는 필드나 사유 enum이 없다.
- 영향: null의 의미가 미제공, 해당 없음, 파싱 오류, 미해결 중 무엇인지 알 수 없다.
- 기본안: 의미 있는 nullable 업무 필드에는 missing_reasons map과 제한된 enum을 사용한다.
- 검증: null+사유 정상, null without reason 거부, null≠0≠빈 문자열.

### DR-007 — 날짜와 시각의 의미가 모호함

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: docs/04는 timezone-aware UTC를 공통 규칙으로 두지만 일봉 예시는 UTC 자정이고, 거래일·date-only와 instant 구분이 없다. 실제 발생 시각을 모르는 event도 timestamp처럼 보인다.
- 영향: 거래소 영업일, DST, 공시일, 실제 발생일을 임의 시각으로 추정할 위험이 있다.
- 기본안: instant만 aware UTC로 저장하고 date-only를 분리한다. 알 수 없는 시각은 null+사유로 둔다.
- 검증: naive datetime 거부, offset 입력의 UTC 정규화, date 유지.

### DR-008 — Data Quality 오류 상태가 계약으로 표현되지 않음

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: Master와 docs/04의 freshness enum에는 ERROR/UNAVAILABLE이 없으나 AGENTS와 Foundation Brief는 정상·지연·오류·미사용 가능 상태를 요구한다.
- 영향: ERROR를 STALE 또는 UNKNOWN으로 왜곡할 수 있다.
- 기본안: availability_status와 freshness_status를 분리하고 last attempt/success/observed/evaluated를 구분한다.
- 검증: ERROR+마지막 정상 데이터 보존, UNAVAILABLE과 UNKNOWN freshness 조합.

### DR-009 — Phase 1 aggregate와 error 계약이 없음

- 분류: 구현 전 해결 필요 / P1 위험
- 근거: Foundation Brief와 Architecture는 system status, securities, company overview, data quality, analysis packet을 요구하지만 docs/04에는 response aggregate와 공통 error schema가 없다.
- 영향: frontend/backend 통합과 HTTP status가 구현자 임의가 된다.
- 기본안: 실행계획 C-12의 endpoint와 envelope를 고정한다.
- 검증: OpenAPI snapshot, generated TypeScript, 200/404/503 schema test.

### DR-010 — 원문과 정규화 hash 요구를 한 필드로 충족할 수 없음

- 분류: P1 위험
- 근거: docs/03 §1은 원문과 정규화 데이터 hash를 모두 보존하라고 하지만 SourceRecord에는 의미가 불명확한 content_hash 하나만 있다.
- 영향: parser 변경, raw 변조, normalized 변화의 원인을 분리할 수 없다.
- 기본안: raw_content_hash와 normalized_content_hash를 분리하고 canonical JSON 규칙을 고정한다.
- 검증: known vector hash, byte 변화와 normalization 변화의 독립 검출.

### DR-011 — raw_storage_ref와 source_locator의 노출 규칙이 없음

- 분류: 보안 P1 위험
- 근거: Data Contracts는 raw_storage_ref와 locator를 정의하고 UI는 원문 링크를 요구하지만, 로컬 path 비노출과 URL scheme 검증이 없다.
- 영향: 로컬 경로 노출, signed URL secret 저장, javascript: URL 또는 unsafe navigation 위험이 있다.
- 기본안: raw ref는 opaque 내부 값으로만 사용하고 UI는 https만 클릭 가능하게 한다. fixture://는 텍스트로 표시한다.
- 검증: javascript:, data:, file: 거부, HTML escape, API에 절대경로 없음.

### DR-012 — SQLite와 Parquet/DuckDB의 Phase 1 범위가 불명확

- 분류: ADR 필요
- 근거: README, Master, Foundation Brief, Acceptance는 SQLite migration을 필수로 본다. Architecture는 시계열을 Parquet/DuckDB에 두고 Phase 1에서 저장 인터페이스와 최소 예시를 검증한다고 한다.
- 영향: Phase 1에서 불필요한 분석 저장소를 구현하거나, 반대로 가격 시계열을 SQLite에 임시 적재해 미래 구조를 훼손할 수 있다.
- 기본안: SQLite는 relational metadata만, 시계열은 validated JSON fixture adapter만 사용하고 Parquet/DuckDB 물리 저장은 이연한다.
- 검증: AnalyticsRepository protocol 존재, DuckDB/Parquet dependency 부재, 시계열 SQLite table 부재.

### DR-013 — fixture 요구와 Acceptance 목록이 다름

- 분류: P1 범위 모호함
- 근거: Foundation Brief는 기관 변화, 공시 문장 변화, valuation scenario, 정정 상태를 요구하지만 docs/11 Phase 1 데이터 목록에는 일부가 빠져 있다.
- 영향: 필요한 fixture가 누락되거나 실제 diff/valuation 엔진으로 범위가 확대될 수 있다.
- 기본안: Foundation Brief의 모든 fixture를 정적 typed sample로 포함하되 계산·parser·diff engine은 만들지 않는다.
- 검증: fixture manifest completeness와 UI의 SAMPLE_RESULT 표시.

### DR-014 — fixture가 실제 데이터처럼 보이지 않게 하는 기준이 없음

- 분류: P1 위험
- 근거: Foundation Brief는 fixture를 실제 기능으로 가장하지 말라고 하지만 자동 기준이 없다.
- 영향: 실제 회사명이나 실제 source 이름과 임의 수치가 함께 보이면 사용자가 실데이터로 오해할 수 있다.
- 기본안: 합성 이름/ticker, data_mode=FIXTURE, source locator fixture://, 항상 보이는 banner를 사용한다.
- 검증: API와 UI fixture marker E2E, 실제 우선 검증 기업명 부재 검사.

### DR-015 — ValuationScenario enum이 직접 충돌

- 분류: P1 계약 충돌
- 근거: docs/04 §12 예시는 assumption_source=USER이고 docs/06 §5 canonical enum은 USER_ASSUMPTION이다.
- 영향: 동일 의미가 두 값으로 저장된다.
- 기본안: USER_ASSUMPTION을 canonical 값으로 사용한다.
- 검증: USER 거부, PER-only static fixture와 scenario 합 1.00.

### DR-016 — Filing change 단일 값과 복수 태그가 충돌

- 분류: P1 계약 충돌
- 근거: docs/04 §8은 change_type 하나를 사용하고 docs/07 §4는 한 문장이 복수 태그를 가질 수 있다고 한다.
- 영향: NUMBER_CHANGED이면서 TONE_DOWN인 변화를 손실한다.
- 기본안: primary_change_type과 change_types 배열을 사용한다.
- 검증: 복수 태그 round-trip, primary가 list에 포함되는지 확인.

### DR-017 — Evidence taxonomy가 서로 직교하지 않음

- 분류: 후속 호환성 위험
- 근거: Master §3.1에는 CALCULATED가 있으나 AssetSquare §2에는 없다. LATEST_VERIFIED는 근거 종류보다 확인 상태에 가깝다.
- 영향: 사실 근거와 최신 확인 상태가 하나의 enum에 섞인다.
- 기본안: evidence_basis와 verification_status를 분리하고 Phase 1에는 엔진·DB table을 만들지 않는다.
- 검증: analysis packet 확장 위치와 enum contract만 확인.

### DR-018 — 금액의 통화·단위가 일부 계약에 없음

- 분류: P1/P0 미래 위험
- 근거: DailyMarketFlow.net_value, InstitutionHolding.market_value_reported, ValuationScenario의 일부 금액은 통화/보고 단위가 불완전하다.
- 영향: 재무 단위 오류와 13F 평가액 오판은 docs/11에서 P0/P1로 분류된다.
- 기본안: Phase 1 fixture에 currency, unit_scale 또는 reported_unit을 명시하고 security currency를 암묵 추론하지 않는다.
- 검증: 통화/단위 누락 거부, 1원/천원/백만원 차이.

### DR-019 — Git workflow를 현재 실행할 수 없음

- 분류: 운영 blocker
- 근거: git rev-parse와 git status가 현재 폴더 및 부모에서 실패한다. docs/12는 Phase branch와 tag를, QA template은 검토 commit을 요구한다.
- 영향: checkpoint, rollback, 독립 리뷰 기준 SHA, secret history scan을 증명할 수 없다.
- 기본안: 현재 프로젝트 폴더를 저장소 루트로 초기화하고 문서 기준 commit 후 Phase branch를 만든다.
- 검증: repo root, branch, clean baseline, commit SHA.

### DR-020 — 승인 테스트가 사례 목록 수준임

- 분류: P1 위험
- 근거: docs/11은 test 종류를 열거하지만 명령, 입력, 기대값, exit code, artifact를 고정하지 않는다.
- 영향: 테스트가 존재해도 요구 충족을 증명하지 못할 수 있다.
- 기본안: 실행계획 §10, §11, §15의 input/expected/command/evidence matrix를 따른다.
- 검증: scripts/test.ps1 하나가 모든 하위 실패를 non-zero로 전파.

### DR-021 — 오프라인 테스트의 경계가 불명확

- 분류: 운영 모호함
- 근거: Architecture는 인터넷 없이 fixture 테스트를 요구한다. 그러나 package와 Playwright browser의 최초 설치는 registry/CDN 접근이 필요하다.
- 영향: setup까지 offline으로 오해하면 의존성 vendoring 없이는 완료 불가능하다.
- 기본안: 최초 setup은 다운로드를 허용하고 setup 완료 후 test/build/E2E는 package 다운로드와 외부 애플리케이션 API 없이 실행한다.
- 검증: pytest socket guard, Playwright non-local request 차단, test.ps1에 install 명령 없음.

### DR-022 — fail-closed와 local security의 자동 기준이 부족

- 분류: 보안 P1 위험
- 근거: Security 문서는 안전한 기본값, localhost, CORS를 요구하지만 반대 설정의 동작과 Host/Origin test를 정의하지 않는다.
- 영향: 환경 누락이나 잘못된 값이 LAN 노출 또는 위험 기능 활성화로 이어질 수 있다.
- 기본안: 위험 flag 반대 값은 startup 실패, 127.0.0.1 bind, exact CORS, trusted host를 적용한다.
- 검증: false configuration test, wildcard origin 거부, 0.0.0.0 policy scan.

### DR-023 — 구조화 로그와 오류 redaction의 schema가 없음

- 분류: 보안 P1 위험
- 근거: Foundation Brief는 구조화 로그와 오류 처리를 요구하고 Security는 포함/제외 항목을 나열하지만 정확한 schema가 없다.
- 영향: token, header, raw payload, path가 log나 traceback에 노출될 수 있다.
- 기본안: request_id/event/source/stage/status/count/duration_ms/error_code allowlist와 redaction을 고정한다.
- 검증: sentinel secret가 captured log, error response, traceback에 없음.

## 5. 후속 Phase의 불가능성·모호함

이 항목들은 Phase 1 구현을 막지 않지만 해당 기능 Phase 전에는 추가 ADR 또는 상세 계약이 필요하다.

### FR-001 — 13F에서 패시브·액티브 보유를 행별로 확정할 수 없음

- docs/05와 docs/13은 비교 UI를 요구하지만 KNOWN_ISSUES KI-004도 공개 13F만으로 전략을 분리하기 어렵다고 인정한다.
- 기관 유형이나 signal weight는 source fact가 아닌 분류/추론으로 표시해야 한다.
- Phase 1에서는 관련 계산을 하지 않는다.

### FR-002 — 13F holding 단위와 reporting identity가 불충분

- InstitutionHolding에 stable holding ID, 보고기간, reported value의 단위·통화가 불완전하다.
- InstitutionHoldingChange의 portfolio weight 분모와 rank_delta 부호 의미도 정의되지 않았다.
- Phase 4 전 P0 단위 오류 방지 계약이 필요하다.

### FR-003 — 기관 합의·혼잡도·sector rotation 공식이 없음

- 추적 universe, 분모, sector taxonomy, 임계값, correction penalty, formula version이 없다.
- 무료 sector 분류 출처도 확정되지 않았다.
- 정적 fixture도 실제 계산 결과처럼 표현하면 안 된다.

### FR-004 — semantic similarity 구현 경로가 없음

- Filing Diff는 의미 유사도를 요구하지만 local model/algorithm, 라이선스, Windows 자원, versioning이 없다.
- OpenAI API는 금지되어 있으므로 Phase 7 전에 별도 무료 로컬 방식과 golden corpus가 필요하다.

### FR-005 — 뉴스 Event 계약이 다종목·다출처를 보존하지 못함

- Event는 issuer_id 하나지만 여러 종목 관련 사건 test가 요구된다.
- source_record_ids는 여러 개인데 headline, source_type, published_at은 하나라 source 충돌·정정을 잃을 수 있다.
- Event–Issuer, Event–Source relation과 별도 Analysis record가 필요하다.

### FR-006 — 뉴스 원문 저장 원칙과 저작권 제한

- Architecture의 connector raw 저장 원칙과 News의 기사 전문 저장 금지가 충돌할 수 있다.
- 뉴스 source별 license/retention 정책이 정해지기 전에는 article body를 raw로 저장하면 안 된다.
- Phase 1 fixture는 완전 합성 제목·요약만 사용한다.

### FR-007 — 무료 consensus/news source가 미확정

- KNOWN_ISSUES KI-002와 docs/03이 출처를 확정하지 못했다.
- PUBLIC_CONSENSUS를 생성하거나 유료 source를 추가하지 않는다.
- future connector 구현 전 비용·약관·freshness 확인이 필요하다.

### FR-008 — 실시간·준실시간 표현은 SLA가 아님

- Master는 실시간·준실시간을 목표로 하지만 Toss 호출 한도와 실제 freshness는 미검증이다.
- Phase 2 전에는 source/API limit dependent로 표현하고 수치 SLA를 약속하지 않는다.

### FR-009 — local admin/settings는 CORS만으로 충분하지 않음

- 미래 변경 endpoint에는 Host/Origin, CSRF, HTTP method, local authentication 경계가 필요하다.
- Phase 1에서는 변경 endpoint 자체를 만들지 않는다.

## 6. 사용자 요구와 직접 관련 없는 범위 확대

Phase 1에서 다음을 구현하면 범위 위반이다.

| ID | 금지할 확대 | 이유 |
|---|---|---|
| SC-01 | 실제 Toss/OpenDART/SEC/news/macro connector | 외부 API 금지 |
| SC-02 | account/token/order service 또는 주문 interface | 읽기 전용 Foundation과 무관 |
| SC-03 | 실제 valuation/DCF/reverse valuation | Phase 6 |
| SC-04 | 실제 filing diff/NLP | Phase 7 |
| SC-05 | 기관 합의·sector rotation·passive/active 계산 | Phase 4/5 |
| SC-06 | AssetSquare rule engine/hypothesis DB | Phase 11 |
| SC-07 | scheduler/background collection | 실제 source 없음 |
| SC-08 | DuckDB/Parquet 물리 저장 | Phase 1 승인 기준에 필수 아님 |
| SC-09 | Settings/Admin 변경 API | 보안 경계 미정 |
| SC-10 | 전체 Market/Smart Money/Valuation/Filings UI | Phase 1은 Company/Data Quality fixture 골격 |
| SC-11 | watchlist, alert, portfolio, calendar, notes | 승인 전 금지 후보 기능 |
| SC-12 | Docker, cloud, LAN 공개, CI/CD | localhost/무료/Windows 우선 범위 밖 |
| SC-13 | backup/restore와 자동 삭제 | v1.0 전 요구이나 Phase 1 최소 범위 밖 |
| SC-14 | chart library와 indicator 계산 | Phase 2/5 기능이며 foundation에 불필요 |

미래 내비게이션은 disabled placeholder로 둘 수 있지만 동작 페이지, 계산 결과 또는 완료 표시를 만들지 않는다.

## 7. 비용 조건 검토

| 항목 | 결과 | 주의 |
|---|---|---|
| OpenAI API | Phase 1 사용 금지로 일치 | package/import/call 정적 검사 필요 |
| 유료 데이터 | Phase 1 사용 없음 | future source 승인 필요 |
| cloud | 사용 없음 | localhost 유지 |
| SQLite | 무료 | 적합 |
| Node/Python toolchain | 무료 | 적합 |
| Playwright | 무료 | 최초 Chromium download 필요 |
| package registry | 금전 비용 없음 | 최초 setup network 필요 |
| GitHub private repo | 권장일 뿐 Phase 1 필수 아님 | 원격 push는 별도 승인 대상 |

현재 문서 안에 Phase 1 비용 조건을 직접 위반하는 요구는 없다.

## 8. 보안 검토

### 현재 상태

- 실제 애플리케이션 코드와 .env가 없다.
- 검토한 문서에서 실제 API key, token, 계좌정보 값은 확인되지 않았다.
- 현재는 Git 저장소가 아니므로 Git history secret scan이나 추적 여부는 증명할 수 없다.
- secret scan 도구는 아직 설치되지 않았다.

### Phase 1 필수 음성 검증

1. 실제 key, private key, bearer token, 고엔트로피 값이 source/fixture/QA/log에 없음
2. .env는 ignore되고 Git tracked file이 아님
3. runtime sentinel secret가 API, log, traceback, HTML, .next/static에 없음
4. frontend에 secret env 또는 server env 전체가 없음
5. openai/broker SDK와 외부 connector dependency가 없음
6. order/account route와 mutation admin endpoint가 없음
7. FastAPI와 Next.js bind가 127.0.0.1
8. wildcard CORS/Host를 허용하지 않음
9. remote font/telemetry/analytics가 없음
10. unsafe source link와 raw local path를 노출하지 않음

## 9. 누락된 자동 완료 기준과 보완

| 누락 | 실행계획 보완 |
|---|---|
| migration 멱등성의 의미 | upgrade twice, schema fingerprint 동일 |
| migration rollback | disposable DB downgrade base 후 re-upgrade |
| fixture import 멱등성 | 두 번째 inserted=0, updated=0, unchanged=N |
| importer 실패 원자성 | invalid fixture에서 transaction 전체 rollback |
| Decimal 정밀도 | large/negative/fraction JSON→DB→API known value |
| timezone | naive 거부, offset→UTC, date-only 보존 |
| null | null+reason, null≠0≠빈 문자열 |
| revision | 원본+정정본 동시 보존, cycle/self-reference 거부 |
| provenance | raw/normalized known SHA-256와 FK |
| API | endpoint별 response schema와 200/404/503 |
| 오류 격리 | 한 source ERROR에서도 health와 다른 카드 유지 |
| UI 상태 | loading/empty/error/not-found component/E2E |
| fixture 진실성 | data_mode, synthetic identity, visible banner |
| 보안 기본값 | 안전 flag 누락과 반대 값 startup test |
| local only | bind/origin/host negative test |
| redaction | canary secret negative assertion |
| offline | localhost 외 socket/request 실패 |
| frontend/backend drift | OpenAPI snapshot과 generated TS diff 0 |
| skip 은닉 | skip/todo/xfail count 0 |
| 완료 증거 | sample JSON, logs, screenshots, commit SHA |

금지어와 skip 검사 범위는 package/lock file, services/api, apps/web, tests, scripts로 제한해야 한다. 미래 비범위를 설명하는 docs, plans, prompts, qa까지 단순 문자열 검색하면 정상 문서가 오탐되므로 자동 검증으로 사용할 수 없다.

## 10. PROPOSED ADR 초안

첨부 지시에 따라 DECISIONS.md는 이번 단계에서 수정하지 않았다. 아래 초안은 실행계획 승인 후 DECISIONS.md에 반영할 제안이다.

### ADR-005 — Phase 1 내부 계약·정밀도·추적 규칙

- 상태: PROPOSED
- 제안일: 2026-08-16

#### 문제

계약 버전, 안정 record ID, Decimal JSON/SQLite 표현, null 사유, raw/normalized hash의 위치가 문서 예시만으로 결정되지 않는다.

#### 제안

- 모든 독립 record와 API envelope에 contract_version 0.1.0을 둔다.
- 모든 normalized record에 안정 ID, natural key, source_record_id, normalized_content_hash를 둔다.
- exact numeric은 Decimal, JSON canonical string, SQLite canonical TEXT로 저장한다.
- 의미 있는 null은 missing_reasons와 함께 저장한다.
- raw_content_hash와 normalized_content_hash를 분리한다.
- aware instant만 UTC Z로 직렬화하고 date-only는 date로 유지한다.

#### 대안

1. JSON number와 SQLite NUMERIC 사용: binary float/affinity 위험으로 기각.
2. envelope에만 버전 표시: 독립 fixture record 검증이 약해져 기각.
3. null 사유를 자유문으로만 저장: 집계·테스트가 어려워 기각.

#### 영향

docs/04의 예시에 필드가 추가되지만 기존 요구를 낮추지 않는다. frontend generated type과 DB migration이 이 규칙을 따른다.

#### 마이그레이션·롤백

Phase 1은 신규 fixture DB라 legacy migration이 없다. ADR이 거부되면 코드 생성 전에 대안 계약으로 계획을 수정한다.

### ADR-006 — Issuer–Security 분리와 route identity

- 상태: PROPOSED
- 제안일: 2026-08-16

#### 문제

issuer_id를 참조하는 계약은 있으나 Issuer 모델과 company route의 ID 의미가 없다.

#### 제안

- Issuer와 Security를 별도 계약/table로 둔다.
- corp_code와 CIK는 issuer, ticker/exchange/share_class/CUSIP/ISIN/FIGI는 security가 소유한다.
- /companies/{issuer_id}는 issuer 기준이며 응답에 선택 security를 명시한다.
- 동일 issuer의 복수 security를 허용한다.

#### 대안

SecurityMaster 하나에 모두 저장: 복수 클래스와 ADR 관계가 모호해져 기각.

#### 영향

최소 Issuer 계약과 table이 Phase 1 파일 목록에 추가된다. 검색·관심종목은 추가하지 않는다.

#### 마이그레이션·롤백

신규 DB라 data migration은 없다. 대안 채택 시 최초 migration 생성 전에 변경한다.

### ADR-007 — Phase 1 SQLite-only metadata와 fixture analytics adapter

- 상태: PROPOSED
- 제안일: 2026-08-16

#### 문제

Phase 1의 명시적 승인 기준은 SQLite migration이지만 Architecture는 Parquet/DuckDB의 최소 예시를 해석상 요구할 수 있다.

#### 제안

- SQLite에는 issuer, security, source record, data quality, import audit만 저장한다.
- 시계열과 분석 sample은 validated read-only JSON fixture adapter로 제공한다.
- AnalyticsRepository protocol을 두고 Parquet/DuckDB 구현은 Phase 2 이후로 이연한다.
- 시계열을 임시로 SQLite에 넣지 않는다.

#### 대안

1. Phase 1에서 DuckDB/Parquet 구현: 범위와 test matrix가 불필요하게 커져 기각.
2. 모든 fixture를 SQLite에 저장: 목표 저장 구조와 달라져 기각.

#### 영향

Phase 1은 storage boundary를 검증하지만 analytics physical persistence는 완료로 주장하지 않는다.

#### 마이그레이션·롤백

fixture adapter는 protocol 뒤에 있으므로 후속 Parquet adapter로 교체 가능하다. legacy data는 없다.

### ADR-008 — Fixture mode, 상태 축, local fail-closed

- 상태: PROPOSED
- 제안일: 2026-08-16

#### 문제

fixture 진실성, freshness/error 구분, unsafe 설정의 실패 동작이 자동 판정 가능하지 않다.

#### 제안

- 모든 API/UI에 data_mode=FIXTURE와 visible banner를 둔다.
- availability, freshness, finality, revision을 별도 enum으로 둔다.
- 실제 회사와 종목을 fixture에 사용하지 않는다.
- 두 서버는 127.0.0.1에만 bind하고 exact local origin/host만 허용한다.
- 위험 flag가 안전한 값이 아니면 startup을 실패한다.
- setup 완료 후 테스트는 localhost 외 outbound network를 차단한다.

#### 대안

경고만 출력하고 실행: 실수로 위험 설정이 활성화될 수 있어 기각.

#### 영향

system status와 Data Quality 계약에 필드가 추가되고 UI/E2E에 fixture assertion이 추가된다.

#### 마이그레이션·롤백

신규 Phase 1 코드이므로 data migration은 없다. local security를 완화하는 변경은 별도 ADR과 사용자 승인이 필요하다.

## 11. OPEN QUESTION

### OQ-01 — 계획·ADR 승인

Phase 1 구현을 시작하려면 plans/PHASE_01_EXECUTION_PLAN.md의 C-01부터 C-12와 위 ADR 기본안의 승인이 필요하다. 안전한 기본안은 실행계획 그대로다.

### OQ-02 — Git 원격 저장소 존재 여부

현재 로컬에는 Git 이력이 없다. 별도 원격 저장소가 있다는 정보도 없다. 기본안은 현재 프로젝트 폴더에 local Git을 초기화하는 것이다. 원격 push나 GitHub 저장소 생성은 이 Phase 0/1 계획에 포함하지 않는다.

그 외 Phase 1 구현을 막는 사용자 선택은 없다. library의 정확한 patch 버전은 Phase 1 scaffold 시 공식 release와 호환성을 확인하고 lockfile에 고정한다.

## 12. Phase 0 완료 기준

| 기준 | 결과 |
|---|---|
| 문서 충돌 목록 | PASS |
| 누락 요구사항 | PASS |
| 지나친 범위 표시 | PASS |
| Phase 1 파일 목록 | PASS |
| Windows 명령 | PASS |
| fixture/contract test 사례 | PASS |
| 비범위 반복 확인 | PASS |
| 실패·롤백·멱등성 | PASS |
| secret scan 방법 | PASS |
| 자동 완료 기준 | PASS |
| application code/config/package/migration 미수정 | PASS |
| Git 기준선 | 미충족 — Phase 1 선행조건 |
| ADR 승인 | 미충족 — 사용자 승인 필요 |

## 13. 최종 판정

Phase 1은 기술적으로 구현 가능하며 비용·읽기 전용 조건을 지킬 수 있다. 그러나 계약 기본안과 저장 경계를 승인하고 Git 기준선을 만든 뒤에만 구현을 시작해야 한다.

**CONDITIONAL PASS**
