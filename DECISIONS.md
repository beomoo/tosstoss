# Architecture Decision Record

## ADR-001 — 초기 운영은 로컬 읽기 전용으로 제한

- 상태: `ACCEPTED`
- 결정일: `2026-08-16`

### 결정
초기 버전은 개인 PC에서 실행되는 로컬 웹 대시보드로 구축한다. 실제 주문과 자동매매는 구현하지 않는다.

### 이유
- 시크릿과 계좌정보 노출 위험을 줄인다.
- 무료 운영 조건을 충족한다.
- 데이터 정확성과 분석 로직을 주문 위험과 분리해 검증한다.

---

## ADR-002 — 전체 문서는 선반영하고 구현은 Phase별로 수행

- 상태: `ACCEPTED`
- 결정일: `2026-08-16`

### 결정
향후 구조를 설명하는 모든 사양서는 저장소에 두되, Codex의 `/goal`은 한 Phase만 수행한다.

### 이유
전체 확장성을 고려하면서도 오류 누적과 대규모 미검증 변경을 방지한다.

---

## ADR-003 — 자산제곱 사고모형은 후속 Phase에서 구현

- 상태: `ACCEPTED`
- 결정일: `2026-08-16`

### 결정
자산제곱 규칙 엔진과 자동 가설 판단은 데이터 계층 검증 후 구현한다. 다만 Phase 1부터 `Evidence`, `Hypothesis`, `InvalidationCondition`, 시나리오 변경 이력에 필요한 인터페이스를 고려한다.

---

## ADR-004 — 기관 수급은 단기 수급과 중기 보유 변화를 분리

- 상태: `ACCEPTED`
- 결정일: `2026-08-16`

### 결정
토스의 개인·외국인·기관 순매수는 단기 흐름으로, SEC 13F와 DART 지분공시는 기관별 중기 포지션 변화로 분리해 분석한다.

---

## ADR-005 — Phase 1 내부 계약·정밀도·추적 규칙

- 상태: ACCEPTED
- 결정일: 2026-08-16

### 결정

- 모든 독립 레코드와 API 응답에 contract_version=0.1.0을 포함한다.
- 모든 정규화 레코드에 안정 ID, 자연키, 원문 연결, 정규화 해시를 둔다.
- 금액·수량·비율은 Decimal로 다루고 JSON canonical decimal string과 SQLite TEXT로 보존한다.
- 의미 있는 null에는 구조화된 결측 사유를 연결한다.
- 원문과 정규화 해시를 분리하고, 시각은 aware UTC, 날짜는 date-only로 보존한다.

### 이유

fixture, DB, API, UI 사이의 정밀도와 재현성을 자동 검증하기 위해서다.

---

## ADR-006 — Issuer와 Security 분리

- 상태: ACCEPTED
- 결정일: 2026-08-16

### 결정

- 발행사와 거래 증권을 별도 계약·테이블로 둔다.
- corp_code와 CIK는 발행사에, ticker, exchange, share class, CUSIP, ISIN, FIGI는 증권에 둔다.
- Company API의 경로 ID는 issuer_id이고 응답에 선택된 security_id를 포함한다.

### 이유

복수 주식 클래스, ADR과 본주, 발행사 공시와 증권 가격을 혼동하지 않기 위해서다.

---

## ADR-007 — Phase 1 저장 경계

- 상태: ACCEPTED
- 결정일: 2026-08-16

### 결정

- Phase 1 SQLite에는 발행사, 증권, 원문 메타데이터, 데이터 품질, fixture import audit만 저장한다.
- 가격·수급·재무·기관 보유 등 시계열 sample은 검증된 read-only JSON fixture adapter로 제공한다.
- Analytics repository protocol을 유지하고 Parquet/DuckDB 물리 저장은 후속 Phase로 이연한다.

### 이유

Foundation의 저장 경계를 검증하면서 실제 connector와 분석 저장소 구현으로 범위가 확대되는 것을 막기 위해서다.

---

## ADR-008 — Fixture mode, 상태 축, 로컬 fail-closed

- 상태: ACCEPTED
- 결정일: 2026-08-16

### 결정

- 모든 API와 UI에 data_mode=FIXTURE를 표시하고 합성 회사·종목만 사용한다.
- availability, freshness, finality, revision 상태를 분리한다.
- 두 서버는 127.0.0.1에만 바인딩하고 정확한 로컬 origin/host만 허용한다.
- 안전 플래그가 반대 값이면 Phase 1 앱은 startup을 실패한다.
- setup 후 test에서는 localhost 외 outbound network를 차단한다.

### 이유

fixture를 실데이터로 오인하거나 잘못된 설정으로 위험 기능·네트워크 노출이 켜지는 일을 방지하기 위해서다.

---

## ADR-009 — Windows Node.js 24.16 이상으로 안전 하한 상향

- 상태: PROPOSED
- 제안일: 2026-08-22

### 문제

최초 기준인 Windows 11 build 26200과 Node.js 24.15.0 조합에서 전체 검증 중 `0xC0000409` 네이티브 TCP 충돌이 재현되었다. 이 종료는 JavaScript 예외로 복구하거나 테스트에서 안전하게 처리할 수 없다.

### 제안

- Node.js 24 계열의 최소 지원 버전을 24.16.0으로 올린다.
- 재현 검증 버전은 현재 LTS인 24.19.0으로 고정한다.
- PowerShell 진입점은 지원하지 않는 Node.js를 실제 빌드·테스트 전에 fail-closed로 거부한다.

### 영향

Node.js 24.15 이하 사용자는 setup, dev, lint, typecheck, build, test, E2E를 실행하기 전에 Node.js를 올려야 한다. 시스템 전역 Node.js를 스크립트가 자동으로 변경하지는 않는다.

### 마이그레이션·롤백

공식 Node.js 24.16 이상으로 업그레이드한다. 하한을 다시 낮추려면 Windows TCP 네이티브 충돌이 제거되었다는 독립 재현 증거가 필요하다.

---

## 새 결정 기록 양식

```md
## ADR-XXX — 제목

- 상태: PROPOSED | ACCEPTED | REJECTED | SUPERSEDED
- 제안일:
- 결정일:

### 문제

### 제안 또는 결정

### 대안

### 영향

### 마이그레이션·롤백
```
