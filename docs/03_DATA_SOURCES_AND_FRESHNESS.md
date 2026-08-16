# Data Sources and Freshness

## 1. 공통 원칙

- 구현 시점의 공식 문서를 우선한다.
- 비공식 스크래핑은 공식 API가 없는 경우에도 별도 승인 없이 추가하지 않는다.
- 원문 데이터와 정규화 데이터의 해시를 보관한다.
- API가 제공하지 않는 값을 추정할 때 `CALCULATED` 또는 `STRUCTURAL_INFERENCE`로 표시한다.
- 소스별 라이선스·호출 조건을 기록한다.
- 화면에는 현재 시각이 아니라 **데이터 기준시각**을 표시한다.

---

## 2. 토스증권 Open API

### 목적
- 국내·미국 주식 종목정보
- 시세·차트
- 국내 투자자별 수급
- 프로그램·공매도·신용·대차
- 향후 계좌 조회는 별도 승인 후 읽기 전용으로 검토

### 주의
- 인증과 토큰은 백엔드 단일 관리자에서 수행
- 허용 IP, 호출 한도, 토큰 갱신 규칙은 공식 문서와 실응답으로 검증
- 브라우저 직접 호출 금지
- 장중 잠정값과 확정값 구분
- WebSocket 또는 스트리밍 지원 여부를 구현 시점 공식 문서로 확인
- 주문 API는 호출하지 않음

### 신선도 예시
구체적 주기는 실 API 한도 확인 후 결정한다.

```text
현재가: 수 초~수십 초 폴링 후보
분봉: 봉 종료 또는 제한에 맞춰 갱신
일봉: 장 종료 후 확정
수급: 소스가 제공하는 잠정·확정 시점에 맞춤
```

---

## 3. OpenDART

### 목적
- 기업 고유번호
- 공시 목록
- 공시 원문
- 분기·연간 재무
- 대량보유
- 임원·주요주주
- 정정·철회 상태

### 주의
- `last_reprt_at=Y`만 사용하면 정정 이력을 잃을 수 있으므로 원본 이력 수집과 현재 유효본 계산을 분리
- 연결·별도 재무 구분
- 단위와 보고서 유형 보존
- 공시 접수번호를 영구 식별자로 활용
- 정정 전후 원문을 모두 보존

---

## 4. SEC EDGAR 및 13F 데이터셋

### 목적
- 기관 제출 이력
- 13F-HR
- 13F-HR/A
- 13F-NT 계열
- 정보표
- 보고기관 관계
- 과거 분기 데이터 적재

### 주의
- 13F는 분기 말 스냅샷이며 실제 매수일·평균단가를 제공하지 않음
- 공시 시차를 화면에 표시
- 주식 수 변화를 평가액 변화보다 우선
- 옵션과 보통주를 분리
- 상위기관과 하위기관 중복 제거
- 수정 공시 처리 후 파생지표 재계산
- SEC 분기 데이터셋은 원문 공시의 대체물이 아니므로 필요 시 원문 확인

---

## 5. 매크로

후보:
- 한국은행 ECOS
- FRED
- 정부·중앙은행 공식 발표
- 거래소·규제기관 공식 데이터

원칙:
- 발표 당시 값과 수정값을 가능한 범위에서 구분
- 시리즈 코드와 단위 보존
- 월·분기 데이터를 일별 값처럼 보간해 사실로 표현하지 않음

---

## 6. 뉴스

후보:
- 합법적인 뉴스 검색 API
- 기업 IR·보도자료
- 거래소·규제기관 공시

원칙:
- 제목·요약·날짜·출처·원문 링크 중심
- 기사 전문 무단 복제 금지
- 같은 사건의 여러 기사는 이벤트로 묶음
- 기사만으로 재무수치 변경 금지
- 공시·실적·기업 발표와 교차 확인

---

## 7. 종목 식별자

```text
internal_security_id
market
exchange
ticker
corp_code
CIK
CUSIP
ISIN
FIGI
share_class
currency
valid_from
valid_to
mapping_status
```

복수 후보는 `UNRESOLVED`로 저장한다.

---

## 8. 공식 참고자료

- 토스증권 Open API: https://corp.tossinvest.com/ko/open-api
- OpenDART 개발가이드: https://opendart.fss.or.kr/guide/main.do
- SEC Form 13F Data Sets: https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets
- SEC EDGAR API: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Codex Best Practices: https://developers.openai.com/codex/learn/best-practices
- Codex Goals: https://developers.openai.com/codex/use-cases/follow-goals
