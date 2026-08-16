# Architecture

## 1. 권장 기술 스택

| 영역 | 기술 | 역할 |
|---|---|---|
| Frontend | Next.js, TypeScript | 웹 대시보드 |
| Backend | FastAPI, Python | 커넥터, 계산, REST API |
| Transactional DB | SQLite | 설정, 메타데이터, 가설, 작업 상태 |
| Analytics storage | Parquet + DuckDB | 가격·수급·기관 보유 시계열 |
| Validation | Pydantic | 입력·출력 데이터 계약 |
| Frontend test | Vitest, Playwright | UI·E2E |
| Backend test | Pytest | 단위·계약·통합 |
| Scheduler | APScheduler 또는 명시적 작업 러너 | 로컬 수집 작업 |
| Chart | ECharts 또는 Lightweight Charts | 금융 차트 |
| Version control | Git | 변경 이력 |
| Runtime | 로컬 Windows | 초기 무료 운영 |

Docker는 선택사항이다. Phase 1의 필수 실행 경로는 Windows PowerShell에서도 동작해야 한다.

---

## 2. 논리 구성

```text
Browser
  ↓
Next.js Web
  ↓
FastAPI
  ├─ Query API
  ├─ Export API
  ├─ Data Quality API
  └─ Admin-local API
        ↓
Domain Services
  ├─ Market Analysis
  ├─ Institutional Flow
  ├─ Financial Normalization
  ├─ Valuation
  ├─ Filing Diff
  ├─ Macro Impact
  └─ Analysis Packet
        ↓
Repositories
  ├─ SQLite
  └─ Parquet/DuckDB
        ↑
Connectors and Jobs
  ├─ Toss
  ├─ OpenDART
  ├─ SEC EDGAR
  ├─ Macro
  └─ News
```

---

## 3. 계층 책임

### Connector
- 공식 API 호출
- 인증
- 호출 한도
- 재시도
- 원문 저장
- 응답 스키마 식별
- 도메인 판단 금지

### Normalizer
- 외부 필드를 내부 계약으로 변환
- 단위·통화·시간대 정규화
- 원문 ID 연결
- 누락 사유 보존

### Repository
- 멱등 적재
- 버전·정정 이력
- 조회
- 트랜잭션
- 마이그레이션

### Domain Service
- 수급 변화
- 가치평가
- 공시 문장 변화
- 매크로 영향
- 기관 합의
- 분석 결과 버전

### API
- UI용 데이터 제공
- 시크릿 비노출
- 페이지네이션
- 입력 검증

### UI
- 기준일과 신선도 표시
- 원문과 추론 구분
- 실패·결측 숨김 금지
- 사용자 가정 편집

---

## 4. 저장 전략

### SQLite
다음과 같은 관계형·작업 상태 데이터:
- security master
- source records
- companies
- managers
- filings
- valuation assumptions
- hypotheses
- jobs
- audit events

### Parquet/DuckDB
다음과 같은 대량 시계열:
- price bars
- daily flows
- short/lending history
- financial fact history
- 13F holdings
- macro series

Phase 1에서는 fixture 데이터로 저장 인터페이스와 최소 예시만 검증한다.

---

## 5. 작업 실행

작업은 데이터 소스별로 분리한다.

```text
fetch → raw persist → validate → normalize → upsert → derive → publish status
```

각 단계는 상태를 기록한다.

```text
PENDING
RUNNING
SUCCEEDED
PARTIAL
FAILED
RETRYING
BLOCKED
```

실패 시 이미 검증된 과거 데이터를 삭제하지 않는다.

---

## 6. API 예시

Phase 1은 fixture 기반 계약만 제공한다.

```text
GET /health
GET /api/v1/system/status
GET /api/v1/securities
GET /api/v1/companies/{id}/overview
GET /api/v1/companies/{id}/data-quality
GET /api/v1/sample/analysis-packet
```

실제 외부 API 연결 엔드포인트는 후속 Phase에서 추가한다.

---

## 7. 환경 분리

```text
APP_ENV=development|test|production
LOCAL_ONLY=true
TRADING_ENABLED=false
DRY_RUN=true
OPENAI_API_ENABLED=false
```

테스트 환경은 인터넷 없이 fixture로 통과해야 한다.

---

## 8. 오류 격리

- 토스 실패가 DART 화면 전체를 막지 않는다.
- SEC 파서 실패가 기존 기관 데이터 삭제로 이어지지 않는다.
- 뉴스 실패가 가치평가 계산을 막지 않는다.
- 각 카드에 소스별 상태를 표시한다.

---

## 9. 변경 원칙

아키텍처 변경은 다음을 포함한 ADR을 작성한다.

- 문제
- 선택
- 대안
- 스키마 영향
- 데이터 마이그레이션
- 롤백
- 테스트
