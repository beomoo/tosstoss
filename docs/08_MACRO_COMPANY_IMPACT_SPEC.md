# Macro-to-Company Impact Specification

## 1. 목적

매크로 지표를 단순 긍정·부정으로 표시하지 않고 기업 실적에 전달되는 인과경로를 구조화한다.

```text
매크로
→ 산업
→ 고객 행동
→ 수주·판매량·가격
→ 매출
→ 마진
→ EPS·현금흐름
→ 가치평가
```

---

## 2. 매크로 레짐

후보 축:

- 성장 가속·둔화
- 인플레이션 상승·하락
- 정책금리
- 장단기금리
- 달러·원화·엔화
- 유동성
- 원유·가스·구리 등 원자재
- 신용스프레드
- 주요 산업 CAPEX
- 정부 정책·규제

레짐은 사용 데이터와 계산 규칙을 표시한다.

---

## 3. 기업 노출 프로필

```yaml
issuer_id: issuer_sample
revenue_regions:
  north_america: 0.40
  korea: 0.35
currency:
  usd_revenue: HIGH
  usd_cost: MEDIUM
  net_usd_effect: POSITIVE
commodity:
  copper_cost: HIGH_NEGATIVE
rates:
  floating_debt: LOW_NEGATIVE
demand_drivers:
  - DATA_CENTER_CAPEX
  - GRID_INVESTMENT
pricing_power: MEDIUM
evidence_ids: []
```

노출 값은 공시·IR·재무에서 근거를 연결한다.

---

## 4. 영향 레코드

```json
{
  "cause": "US_DATA_CENTER_CAPEX_UP",
  "effect": "POWER_EQUIPMENT_DEMAND_UP",
  "issuer_id": "issuer_...",
  "direction": "POSITIVE",
  "strength": "MEDIUM",
  "lag": "2_TO_4_QUARTERS",
  "mechanism": "데이터센터 건설 증가가 배전설비 발주를 늘릴 가능성",
  "supporting_evidence_ids": [],
  "counter_evidence_ids": [],
  "unconfirmed_items": [],
  "confidence": 0.70
}
```

---

## 5. 직접·간접 영향

### 직접
- 환율 환산
- 원재료
- 이자비용
- 에너지 비용
- 세율·규제

### 간접
- 고객 CAPEX
- 경기 수요
- 공급망
- 경쟁 증설
- 가격결정력
- 시장 멀티플

직접 영향과 간접 영향을 한 점수로 뭉개지 않는다.

---

## 6. 시차

```text
IMMEDIATE
0_TO_1_QUARTER
2_TO_4_QUARTERS
1_TO_2_YEARS
LONG_TERM
UNKNOWN
```

매크로 지표 발표일과 실적 반영시점을 구분한다.

---

## 7. 반론과 무효화

각 긍정 경로에는 가능한 반대 경로를 둔다.

예:
```text
데이터센터 CAPEX 증가
→ 전력기기 수요 증가

반론
→ 고객의 건설 지연
→ 경쟁사 증설
→ 원자재 상승
→ 주문 취소
→ 이미 높은 가격에 반영
```

---

## 8. 가치평가 연결

매크로 영향은 다음 순서로만 가치평가에 반영한다.

1. 근거 있는 사업 변수 변화
2. 매출·마진 시나리오 가정 변경
3. 계산 재실행
4. 변경 사유 기록

매크로 방향만으로 EPS를 임의 변경하지 않는다.

---

## 9. 필수 테스트

- 환율의 매출·원가 양방향
- 원자재 상승
- 금리 상승
- 고객 CAPEX 시차
- 상반된 노출
- 근거 없음
- 반론
- 무효화 조건
- 시나리오 입력 변경 이력
