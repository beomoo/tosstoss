# Master Implementation Plan

## 1. 목표

토스증권 Open API와 기업분석 데이터를 연결해 다음 기능을 제공하는 개인용 실시간·준실시간 웹 대시보드를 구축한다.

1. 매크로 변화가 기업에 미치는 직접·간접 영향
2. 차트·거래량·상대강도 분석
3. 기사, 공시, 실적, 주요 이벤트 확인
4. 국내 단기 수급과 글로벌 기관 포지션 변화 분석
5. 안전마진과 Bear/Base/Bull 가격 시나리오
6. 연도·분기 공시 문장을 비교한 신규·삭제·톤업·톤다운 탐지
7. 모든 판단의 출처, 기준일, 수정 이력, 미확인 항목 표시
8. ChatGPT Plus에서 후속 추론에 사용할 분석 패킷 생성

현재 목표는 **투자 판단을 보조하는 읽기 전용 연구 시스템**이며, 실제 주문 시스템이 아니다.

---

## 2. 비용·운영 조건

- 추가 OpenAI API 비용: 사용하지 않음
- ChatGPT: Plus 범위에서 수동 분석 패킷 활용
- 클라우드 서버: 초기에는 사용하지 않음
- 데이터베이스: 무료 로컬 도구
- 유료 시세·컨센서스: 사용하지 않음
- 운영 환경: Windows 개인 PC 우선
- 저장소: 비공개 GitHub 권장
- 배포: `localhost` 우선

---

## 3. 핵심 설계 원칙

### 3.1 사실과 추론 분리

```text
DIRECT_SOURCE      공시·API 원문에서 직접 확인
CALCULATED         공식 입력으로 계산
STRUCTURAL_INFERENCE 여러 사실을 연결한 구조적 추론
LATEST_VERIFIED    최신 데이터로 재확인
UNCONFIRMED        공개 데이터로 확인되지 않음
```

### 3.2 시간 구분

모든 데이터에 가능한 범위에서 다음 시간을 분리한다.

```text
observed_at   데이터가 의미하는 기준시점
published_at  원문 발표·공시 시각
filed_at      규제기관 제출 시각
fetched_at    시스템 수집 시각
effective_at  정정·적용 효력 시각
```

### 3.3 데이터 상태

```text
freshness_status: FRESH | STALE | EXPIRED | UNKNOWN
finality_status: PRELIMINARY | FINAL | REVISED | UNKNOWN
revision_status: ORIGINAL | AMENDED | SUPERSEDED | MERGED
```

### 3.4 분석 결과의 재현성

- 계산식 버전
- 입력 데이터 ID
- 소스 원문 ID
- 계산 실행시각
- 사용자 가정
- 코드 버전 또는 commit SHA

를 남긴다.

---

## 4. 단계별 로드맵

### Phase 0 — 문서·계획 검토

- 문서 간 충돌과 누락 탐지
- Phase 1 실행계획 생성
- 코딩 금지

### Phase 1 — Foundation

- Next.js + TypeScript
- FastAPI + Python
- SQLite 마이그레이션
- 저장소 인터페이스
- fixture 기반 샘플 화면
- 공통 데이터 계약
- 테스트·로그·보안 기반
- 외부 API 연결 금지

### Phase 2 — 토스증권 읽기 전용 데이터

- 인증과 토큰 관리
- 종목 마스터
- 현재가
- 일봉·분봉
- 국내 투자자별 순매수
- 프로그램·공매도·신용·대차
- 호출 한도·오류·신선도 처리

### Phase 3 — OpenDART

- 기업 고유번호 매핑
- 공시 목록과 원문
- 정기 재무제표
- 대량보유
- 임원·주요주주
- 정정·철회 공시 이력

### Phase 4 — SEC 13F

- 기관 CIK 등록
- 13F-HR, 13F-HR/A, 13F-NT 계열
- 과거 데이터셋 적재
- 신규 제출 감지
- CUSIP 매핑
- 기관 상하위 관계
- 주식 수 기반 분기 변화
- 섹터 로테이션과 합의 신호

### Phase 5 — 대시보드 기본 화면

- Market Overview
- Company Dashboard
- Smart Money
- Disclosures & Events
- Data Quality

### Phase 6 — 가치평가

- PER
- PBR
- EV/EBITDA
- 간소화 DCF
- 현재 주가의 내재 기대 역산
- 안전마진
- Bear/Base/Bull
- 가정 변경 이력

### Phase 7 — 공시 문장 비교

- 섹션 정규화
- 신규·삭제·수정
- 숫자 변화
- 톤업·톤다운
- 불확실성 증가·감소
- 원문 대조

### Phase 8 — 매크로·기업 영향

- 매크로 레짐
- 기업 노출 프로필
- 직접·간접 영향
- 반영 시차
- 근거와 반대 근거
- 무효화 후보

### Phase 9 — 뉴스·이벤트와 분석 패킷

- 뉴스 메타데이터와 원문 링크
- 이벤트 중복 제거
- 실적·공시와 교차 확인
- `analysis_packet.json`
- `analysis_packet.md`
- `source_manifest.json`

### Phase 10 — 통합 안정화

- 장애 복구
- 백업·복원
- 실제 샘플 대조
- 장기 수집
- 전체 데이터 QA
- 읽기 전용 v1.0

### Phase 11 — 자산제곱 사고모형

- 투자 가설 원장
- 강화·약화·반전·신규
- 인과관계 그래프
- 시장 기대와 실제 변화 차이
- 무효화 조건
- 6~18개월 손익비
- 원문 규칙 검증 후 단계적 적용

### Future — 별도 승인 필요

- 가상 포트폴리오
- 모의주문
- 실제 주문
- 자동매매

실제 주문 기능은 본 계획의 기본 완료 범위가 아니며 별도 보안·위험관리 프로젝트로 분리한다.

---

## 5. 단계 진입 게이트

다음 Phase로 넘어가려면:

- P0 버그 0개
- P1 버그 0개
- P2는 수정 또는 명시적 이월 승인
- 필수 테스트 전부 PASS
- 실제 또는 fixture 원문 대조 PASS
- 보안 검사 PASS
- `STATUS.md`, `CHANGELOG.md`, QA 문서 갱신
- 미확인 사항은 `KNOWN_ISSUES.md`에 기록

---

## 6. 우선 검증 종목·기관

초기 fixture와 소규모 실제 검증은 유형이 다른 종목과 기관으로 구성한다.

### 국내 기업 예시
- LS ELECTRIC
- HD현대일렉트릭
- 효성중공업
- 세아제강지주

### 미국 기업 예시
- NVIDIA
- AMD
- Broadcom
- Microsoft

### 기관 예시
- BlackRock
- Goldman Sachs
- Berkshire Hathaway
- Coatue Management

실제 종목코드·CIK·CUSIP은 커넥터 구현 시 공식 원문으로 검증한다.

---

## 7. 사용자 승인 지점

사용자가 매 줄의 코드를 확인할 필요는 없다. 다음 지점에서만 승인한다.

1. Phase 계획
2. 구현 결과와 자체 QA
3. 독립 리뷰와 실제 데이터 대조
4. 다음 Phase 진입

---

## 8. 최종 성공 기준

읽기 전용 v1.0은 다음이 가능해야 한다.

- 기업별 최신 가격·실적·공시·수급을 기준일과 함께 확인
- 국내 단기 수급과 글로벌 기관 보유 변화를 분리
- 13F의 지연·패시브 효과·수정 공시 한계 표시
- 가치평가 가정을 직접 수정하고 결과 재계산
- 공시 문장 변화의 이전·현재 원문 대조
- 매크로 변화의 기업 영향 경로와 반론 표시
- 분석 결과를 ChatGPT Plus용 구조화 패킷으로 내보내기
- 소스 오류나 지연을 숨기지 않고 데이터 품질 화면에 표시
