# Known Issues and Open Questions

## KI-001 — 토스증권 실제 API 세부 계약 미검증

- 상태: `OPEN`
- 영향: 공개 계약은 2026-08-23 기준 OpenAPI v1.2.14에서 확인했지만 실제 토큰 발급, 허용 IP, runtime rate header·`Retry-After`, 응답/error와 provider timing은 credential을 사용한 실응답으로 확인하지 않았다.
- 현재 대응: `plans/PHASE_02_EXECUTION_PLAN.md`에 공개 계약과 `[LIVE_UNVERIFIED]`를 분리했다. CP2-B의 OAuth/exact HTTP boundary와 CP2-C의 shared limiter·bounded retry는 합성 credential, MockTransport와 fake time으로 offline 검증했다. 독립 검토·사용자 승인 후 CP2-D의 별도 credential preflight에서만 secret을 출력·저장하지 않고 live 항목을 검증한다.

## KI-002 — 무료 미래 컨센서스 데이터의 안정적 출처 미확정

- 상태: `OPEN`
- 영향: 향후 EPS·PER 기반 목표가 계산에서 시장 컨센서스 자동 수집이 제한될 수 있다.
- 현재 대응: 공시 실적, 사용자 가정, 내재 기대 역산을 우선한다.

## KI-003 — 13F CUSIP-티커 매핑의 불확실성

- 상태: `OPEN`
- 영향: 복수 후보, 회사채·옵션·클래스 주식 등에서 오매핑 위험이 있다.
- 현재 대응: 매핑 실패를 `UNRESOLVED`로 저장하고 임의 결합하지 않는다.

## KI-004 — 대형 운용사의 패시브·액티브 보유 분리 한계

- 상태: `OPEN`
- 영향: BlackRock, Vanguard 등의 보유 증가는 지수·ETF 자금 효과일 수 있다.
- 현재 대응: 기관 유형 가중치와 제한사항을 표시하며 투자 확신의 직접 근거로 단독 사용하지 않는다.

## KI-005 — 공시 문장 비교의 양식 변경 오탐

- 상태: `OPEN`
- 영향: 섹션 이동, 표 변환, 문단 재배치가 내용 변화로 오인될 수 있다.
- 현재 대응: 동일 문서 유형 우선 비교, 섹션 정렬, 숫자 diff 분리, 원문 대조 UI를 요구한다.

## KI-006 — Node.js 24.15 이하 Windows 네이티브 TCP 충돌

- 상태: `MITIGATED`
- 영향: Windows에서 짧은 TCP 연결을 반복하는 빌드·런타임 사전검사가 JavaScript 오류 없이 `0xC0000409`로 종료될 수 있다.
- 현재 대응: Node.js 24.16 이상만 허용하고 `.node-version`과 최종 QA 기준을 24.19.0으로 고정한다. 프로젝트 스크립트는 구버전을 작업 시작 전에 거부한다.

## KI-007 — 공식 WebSocket 문서 상태 충돌

- 상태: `OPEN`
- 확인일: `2026-08-23`
- 대화형 문서 statement: `developers.tossinvest.com/docs/market-data`의 색인된 설명에는 “웹 소켓은 추후 지원 예정”이 남아 있다.
- canonical developer source statement: `developers.tossinvest.com/llms.txt`, 공식 overview와 AsyncAPI v1.2.2는 `wss://openapi-ws.tossinvest.com/ws/v1` 및 Trade·Orderbook·Order Event channel을 정의한다.
- 영향: 문서 UI/cache만 보면 REST-only로 오판할 수 있다. 반대로 WebSocket 전체를 범용 구현하면 금지된 개인 주문 이벤트 surface까지 들어올 수 있다.
- Phase 2 결정: canonical AsyncAPI의 존재를 인정하되 Phase 2 runtime은 범위 제한상 REST polling only로 고정한다. WebSocket host와 code는 allowlist에 넣지 않는다.
- 재검토 조건: 별도 WebSocket checkpoint, 시세 channel만의 보안 경계, order-event 제외 policy와 사용자 승인이 모두 준비될 때 재검토한다.

## KI-008 — Toss response의 명시적 finality flag 부재

- 상태: `OPEN`
- 영향: 공식 문서가 장중 잠정·저녁 확정·T+1 반영 시점을 설명하지만 scoped REST response에는 공통 finality boolean/enum이 없다. 장 종료만으로 `FINAL`을 만들면 후속 갱신을 누락할 수 있다.
- 현재 대응: 명백한 장중 값만 `PRELIMINARY`, 나머지는 기본 `UNKNOWN`으로 계획했다. CP5 live 관찰에서 deterministic 전환 조건을 검증하고 승인하기 전에는 자동 `FINAL`을 사용하지 않는다.

## KI-009 — Phase 1 SourceRecord와 date-only 시장 데이터의 시간 의미 차이

- 상태: `OPEN`
- 영향: 필수 `observed_at`·`published_at`에 date-only 기준일이나 fetch 시각을 대입하면 기준일과 수집일을 혼동한다.
- 현재 대응: ADR-011과 Phase 2 계획에서 기존 v0.1.0을 유지하는 versioned provider source contract를 제안했다. CP3 전에 승인되지 않으면 date-only normalized publish를 시작하지 않는다.
