# Institutional Flow Specification

## 1. 목적

기관 수급을 다음 두 층으로 분리한다.

```text
단기 시장 수급
- 개인
- 외국인
- 기관
- 프로그램
- 공매도
- 신용·대차

중기 기관 포지션
- SEC 13F
- DART 대량보유
- DART 임원·주요주주
- 기관별·섹터별 포지션 변화
```

---

## 2. 13F 해석 원칙

- 분기 말 보유 스냅샷이다.
- 실제 매수·매도 날짜와 평균가격은 알 수 없다.
- 공시 제출일과 보유 기준일을 분리한다.
- 시장가치보다 보유주식 수 변화를 우선한다.
- 시장가치 증가만으로 추가매수로 분류하지 않는다.
- 보통주, PUT, CALL, 클래스 주식을 분리한다.
- 비미국 거래소 보유와 공매도 등 미보고 범위를 제한사항으로 표시한다.
- 원문 제출과 SEC 분기 데이터셋을 대조할 수 있어야 한다.

---

## 3. 공시 유형 처리

### 13F-HR
정상 보유보고.

### 13F-HR/A
수정 유형을 확인한다.

- 기존 전체를 대체하는 restatement
- 누락 보유항목 추가
- 기타 수정

수정 원문을 보존하고 현재 유효본을 계산한다.

### 13F-NT
보유 0으로 처리하지 않는다. 다른 보고기관에 포함됐는지 관계를 해석한다.

### Combination Report
상위·하위 보고기관 관계를 저장하고 이중 집계를 방지한다.

---

## 4. 기관 유형

```text
PASSIVE_LARGE_MANAGER
ACTIVE_ASSET_MANAGER
HEDGE_FUND
BANK_DEALER_GROUP
PENSION_FUND
SOVEREIGN_FUND
INSURANCE
UNKNOWN
```

기관 유형은 신호의 해석 가중치일 뿐 사실을 변경하지 않는다.

---

## 5. 변화 분류

```text
NEW
AGGRESSIVE_ADD
ADD
HOLD
TRIM
AGGRESSIVE_REDUCE
EXIT
PERSISTENT_BUILD
PERSISTENT_DISTRIBUTION
SECTOR_ROTATION_IN
SECTOR_ROTATION_OUT
```

초기 임계값은 하드코딩하지 않고 버전 관리되는 설정으로 둔다. 임계값 변경은 과거 결과 재현성을 위해 버전을 남긴다.

---

## 6. 비교 우선순위

1. 보유주식 수
2. 포트폴리오 비중
3. 기관 내 보유 순위
4. 평가액
5. 주가 효과 추정

추정치는 `estimated` 필드와 제한사항을 가진다.

---

## 7. 기관 합의 신호

```text
CONSENSUS_BUILD
CONSENSUS_REDUCE
ACTIVE_PASSIVE_DIVERGENCE
SMART_MONEY_DIVERGENCE
DISTRIBUTION_DIVERGENCE
CROWDED_LONG
CROWDED_EXIT_RISK
```

신호 구성요소:

- 추적 기관 중 방향 비율
- 기관 유형
- 연속 분기
- 주식 수 변화
- 비중 변화
- 보고 시차 감점
- 수정 공시 감점
- 매핑 불확실성
- 동일 상위그룹 중복 제거

---

## 8. 국내 주식

한국 종목은 13F만으로 판단하지 않는다.

```text
토스 외국인·기관 일별 수급
+
DART 대량보유
+
DART 주요주주
+
외국인 보유율
=
국내 자금 흐름
```

개별 해외기관 전체 보유가 공개되지 않는 경우 `UNAVAILABLE`로 표시한다.

---

## 9. 펀더멘털 연결 원칙

기관 포지션 변화가 직접 변경할 수 없는 값:

- 매출
- 영업이익
- EPS
- 목표 PER
- DCF 현금흐름

기관 변화가 영향을 줄 수 있는 값:

- 투자 가설 신뢰도
- 시나리오 확률
- 수급 지속성
- 혼잡도
- 진입 시점 참고
- 추가 확인 우선순위

실적·공시와 방향이 일치할 때만 가설 강화 신호의 근거로 사용한다.

---

## 10. 화면 요구사항

### Smart Money Overview
- 최신 보고기간
- 제출 지연
- 기관 합의
- 신규·전량매도
- 섹터 로테이션

### Manager Detail
- 기관 유형
- 보고구조
- 분기별 총 보유
- 신규·확대·축소
- 상위 보유
- 제한사항

### Company Institutional Ownership
- 기관별 주식 수 변화
- 패시브·액티브 분리
- 연속 변화
- 가격과의 괴리

### Filing Revision History
- 원본
- 수정본
- 유효본
- 재계산된 신호
- 기존 알림 정정

---

## 11. 필수 테스트

1. 보유주식 수 증가
2. 평가액만 증가하고 수량 동일
3. 신규 편입
4. 전량 매도
5. 일반 수정본 대체
6. 누락 항목 추가 수정
7. 13F-NT
8. Combination Report
9. 상위·하위기관 이중 집계
10. PUT/CALL 분리
11. CUSIP 매핑 실패
12. 보고 기준일과 제출일
13. 수정 후 합의 점수 재계산
14. 국내 대량보유 정정
15. 결측을 0으로 처리하지 않음
