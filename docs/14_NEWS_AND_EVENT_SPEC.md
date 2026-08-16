# News and Event Specification

## 1. 목적

기사, 공시, 실적, 기업 발표를 하나의 사건 타임라인으로 통합하되 원문 유형과 신뢰도를 구분한다.

---

## 2. 이벤트 유형

```text
EARNINGS
GUIDANCE
CONTRACT
CAPEX
PRODUCT
REGULATION
LITIGATION
FINANCING
EQUITY_ISSUANCE
OWNERSHIP
MANAGEMENT
CUSTOMER_CAPEX
MACRO_POLICY
OTHER
```

---

## 3. 데이터

```json
{
  "event_id": "evt_...",
  "issuer_id": "issuer_...",
  "event_type": "EARNINGS",
  "headline": "제목",
  "summary": "허용된 요약",
  "occurred_at": "2026-08-14T00:00:00Z",
  "published_at": "2026-08-14T01:00:00Z",
  "source_type": "REGULATORY_FILING",
  "source_record_ids": [],
  "dedupe_group_id": "group_...",
  "verification_status": "CROSS_VERIFIED",
  "impact_horizon": "MEDIUM_TERM",
  "analysis_direction": "POSITIVE",
  "confidence": 0.80
}
```

방향과 확신도는 원문 필드가 아니라 분석 결과임을 구분한다.

---

## 4. 우선순위

```text
규제 공시
기업 IR·보도자료
거래소·정부 공식 발표
신뢰도 높은 뉴스
기타
```

기사와 공식 공시가 충돌하면 공식 원문을 우선하고 충돌 사실을 표시한다.

---

## 5. 중복 제거

- 같은 발표
- 같은 수치
- 유사 제목
- 원문 링크
- 시간 근접성
- 관련 공시 ID

중복 기사는 하나의 이벤트 아래 출처 목록으로 묶는다.

---

## 6. 저작권

- 기사 전문 저장·재배포 금지
- 제목, 짧은 요약, 메타데이터, 원문 링크 중심
- 공시·공식 자료는 해당 이용조건 준수
- 원문 스냅샷 저장 여부는 소스 약관 검토 후 결정

---

## 7. 가설 연결

이벤트는 다음으로 연결될 수 있다.

- supporting evidence
- contradicting evidence
- unconfirmed
- invalidation candidate

기사 제목만으로 가설 상태를 자동 변경하지 않는다.

---

## 8. 필수 테스트

- 동일 사건 중복
- 공시와 기사 충돌
- 날짜 불일치
- 원문 링크
- 기사 전문 미저장
- 기업 매핑 실패
- 여러 종목 관련 사건
