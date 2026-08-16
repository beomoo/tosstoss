# Valuation Specification

## 1. 목적

하나의 목표주가를 정답처럼 보여주지 않고, 평가방법·가정·시나리오·현재 주가에 내재된 기대를 함께 보여준다.

---

## 2. 평가방법

### PER
```text
Implied Price = Forecast EPS × Target PER
```

### PBR
```text
Implied Price = Forecast BPS × Target PBR
```

### EV/EBITDA
```text
Enterprise Value = Forecast EBITDA × Target Multiple
Equity Value = Enterprise Value - Net Debt + Non-operating Assets
Price = Equity Value / Diluted Shares
```

### DCF
- 명시적 예측기간
- FCFF
- WACC
- 영구성장률 또는 Exit Multiple
- 순차입금
- 희석주식수
- terminal value 비중 경고

### Reverse Valuation
현재 주가를 정당화하는 다음 값을 역산한다.

- EPS
- 매출 성장률
- 영업이익률
- 목표 멀티플
- 장기 성장률

---

## 3. 시나리오

```text
BEAR
BASE
BULL
```

각 시나리오는 다음을 가진다.

- 가정
- 출처
- 기간
- 확률
- 평가방법
- 적정가치
- 주요 촉매
- 무효화 조건
- 변경 이력

확률 합계는 100%여야 한다.

---

## 4. 안전마진

```text
Margin of Safety = (Fair Value - Current Price) / Fair Value
```

확률가중 가치:

```text
Expected Value = Σ(Scenario Value × Probability)
```

현재 가격이 적정가치보다 높으면 안전마진은 음수가 될 수 있다.

---

## 5. 입력 출처

```text
DISCLOSED_ACTUAL
CALCULATED_HISTORY
USER_ASSUMPTION
PUBLIC_CONSENSUS
SYSTEM_INFERENCE
```

무료 데이터로 신뢰할 수 있는 컨센서스를 확보하지 못하면 `PUBLIC_CONSENSUS`를 임의 생성하지 않는다.

---

## 6. 수치 원칙

- 연결·별도 구분
- 계속사업·중단사업 구분
- 일회성 손익 표시
- 희석주식수
- 통화
- 단위
- 회계연도
- trailing과 forward 구분
- 음수 EPS의 PER 처리
- 순현금 기업의 EV bridge
- 금융업 등 부적절한 방법 경고

---

## 7. 기관·차트 연결 제한

기관 매수, 차트 상승, 뉴스 긍정은 EPS나 DCF를 직접 변경하지 않는다.  
기관 포지션은 시나리오 확률과 검증 우선순위에만 제한적으로 반영할 수 있다.

---

## 8. 화면

- 현재 가격
- 확률가중 가치
- 안전마진
- 시나리오 표
- 평가방법별 결과
- 민감도 표
- 현재 주가 내재 기대
- 입력 가정과 출처
- 최근 변경 사유

---

## 9. 필수 테스트

- PER 정상
- 음수 EPS
- PBR
- EV-to-equity bridge
- 순현금
- DCF terminal value
- 확률합 100%
- 단위 1원/천원/백만원
- 통화 변환
- null 처리
- 현재가 0 또는 누락
- 수동 계산 대조
- 가정 변경 이력
