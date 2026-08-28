# Known Issues and Open Questions

## KI-001 — 토스증권 실제 API 세부 계약 부분 검증

- 상태: `OPEN — PARTIALLY LIVE VERIFIED`
- `[LIVE_VERIFIED]`: 2026-08-24 사용자 독립 CP2-D2 one-shot에서 canonical provider contract(OpenAPI `3.1.0`, provider `1.2.14`, origin/hash 일치), actual OAuth token issuance와 credential acceptance, allowed-IP 실행 경로, actual `GET /api/v1/stocks` 구조, 성공 응답의 `X-RateLimit-Limit`·`Remaining`·`Reset` 유효성을 safe fixed summary로 확인했다.
- `[LIVE_UNVERIFIED]`: natural 429 `Retry-After`, actual 429/5xx behavior, production retry timing, 나머지 Phase 2 market endpoint, CP3 이후 데이터 semantics/freshness. natural 429를 고의로 유도하지 않았으므로 `Retry-After`를 verified로 올리지 않는다.
- 현재 대응: CP2-B/C의 exact boundary·single-flight·bounded retry와 cumulative-wait ceiling은 MockTransport/fake time 회귀로 유지한다. live 미검증 항목은 해당 후속 checkpoint에서 최소 요청으로 별도 검증하며 credential 값, token, body와 raw header 값은 QA evidence에 저장하지 않는다.

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

- 상태: `OPEN — CONTRACT FOUNDATION IMPLEMENTED / LIVE SEMANTICS UNVERIFIED`
- 영향: 필수 `observed_at`·`published_at`에 date-only 기준일이나 fetch 시각을 대입하면 기준일과 수집일을 혼동한다. 기존 ADR-011의 “observed time/date 중 최소 하나”도 공식 `/prices timestamp=null` 상태를 표현하지 못한다.
- 현재 대응: ADR-011은 2026-08-25 `ACCEPTED`다. CP3-B의 별도 `toss-source/0.1.0` contract는 기존 v0.1.0을 유지하면서 observed time/date 둘 다 null + structured reason을 표현하고 dataset별 조합을 fail closed한다. CURRENT_PRICE freshness는 CP3-D2 승인 전 timestamp 유무와 무관하게 `UNKNOWN`이며 timestamp-null source는 보존하되 latest pointer에는 사용할 수 없다. 실제 `/prices` timestamp-null 빈도·의미와 freshness는 계속 live unverified이며 CP3-D 전에는 user-facing price publish를 구현하지 않는다.

## KI-011 — Toss issuer/security identity와 Phase 1 regulatory ID 충돌

- 상태: `MITIGATED — ADR-012 ACCEPTED / CP3-C1 PROVIDER RECONCILIATION IMPLEMENTED / CANONICAL PROMOTION DEFERRED`
- 영향: Toss stock response에는 Phase 1 `Issuer`가 KR/US별로 요구하는 corp_code/CIK가 없다. Toss symbol/ticker/name 또는 synthetic ID로 채우면 잘못된 issuer merge, share-class 혼동과 P0 mapping 오류가 생긴다. 반대로 verified canonical mapping을 모든 price storage의 전제조건으로 두면 Phase 2가 Phase 3/4 regulatory mapping에 순환 의존한다. 현재 근거로 exchange도 확정할 수 없다.
- 현재 대응: CP3-C1은 Toss name/symbol/ISIN만으로 canonical Issuer/Security를 만들거나 `VERIFIED`로 승격하지 않고 provider staging에서 중단한다. conservative KR/US common-equity 후보만 eligible evidence로 표시하고 unsupported/contradictory/collision은 격리한다. fake corp_code/CIK와 exchange 추정은 0이다. canonical promotion authority는 CP3-C2 `USER_DECISION_REQUIRED`, ProviderPriceSnapshot은 CP3-D 비범위로 남는다.

## KI-012 — 반복 price/revision과 기존 source record natural key 충돌

- 상태: `MITIGATED — CP3-B SOURCE IDEMPOTENCY/TRACE HARDENED / PRICE USE DEFERRED`
- 영향: 기존 `source_records(source_system, source_type, external_id)` unique는 같은 request의 반복 price snapshot과 same-key payload revision을 모두 보존할 수 없다. external ID에 현재 시각을 붙이면 멱등성을 우회하고 deterministic rebuild가 깨진다.
- 현재 대응: 기존 table/`0001`/`0002`를 byte-identical로 유지하고 신규 `provider_source_versions`의 request/status/raw-hash/contract unique, deterministic source ID, self-FK supersession과 provider latest pointer를 구현했다. 같은 raw/source를 나중에 재수집하면 `fetched_at`·safe telemetry 차이를 semantic duplicate로 처리해 first-seen manifest를 유지하지만 dataset/parser/normalized hash/revision link 차이는 conflict로 차단한다. additive `0003`은 request별 ORIGINAL root와 non-null supersedes parent를 각각 unique partial index로 보호하고 repository는 unique current leaf만 supersede하는 전체 linear chain을 검증한다. exact path→dataset/request→raw→source→attempt/audit graph와 atomic source+audit rollback도 offline test로 고정했다. 실제 반복 price snapshot은 CP3-D 전까지 적재하지 않는다.

## KI-013 — provider identity identifier enrichment reconciliation

- 상태: `MITIGATED — CP3-C1 FUNCTIONALLY APPROVED / DOCUMENTATION CLOSEOUT PUSHED FOR FINAL GPT CHECK`
- 영향: ISIN/listDate가 없는 최초 observation으로 provider identity를 만든 뒤 후속 observation에 강한 identifier가 등장할 수 있다. 매 observation마다 anchor 우선순위를 다시 적용하면 같은 instrument에 새 ID가 생기고 price/history continuity와 deterministic rebuild가 깨진다.
- 현재 대응: CP3-C1은 기존 active identity/history continuity를 최초 anchor보다 먼저 검색하고, 단일 비모순 후보는 같은 ID를 재사용해 ISIN/listDate/symbol history만 추가한다. 독립검토 P1 보완으로 current identifier는 closed/open/SYMBOL_CHANGE 의미를 source chronology에서 해석하며 history ID/hash로 winner를 선택하지 않는다. 상충 current value는 fail closed한다. 한 detail source의 duplicate non-null ISIN도 publish 전에 batch-level로 계획해 affected observation 전부를 처음부터 non-eligible collision quarantine으로 기록한다. 동일 append-only source history와 response order variation의 canonical dump 회귀를 유지한다. GPT independent re-review는 P1-01·P1-02를 CLOSED로 판정했으며, CP3-C2 canonical promotion authority는 계속 `USER_DECISION_REQUIRED`다.

## KI-014 — secret-scan randomized self-canary intermittent behavior

- 상태: `OPEN — NONBLOCKING QA INFRASTRUCTURE P2`
- 관찰: CP3-C1 Codex self-report의 final successful run 전 실행 기록에서 변경되지 않은 secret-scan의 randomized self-canary가 간헐적으로 자체 거부 조건을 만족하지 못한 현상이 관찰됐다. 이후 독립 secret-scan과 최종 전체 회귀에서는 PASS했다.
- 영향: 랜덤 self-canary의 재현성에 관한 비차단 QA infrastructure P2다. repository secret 노출이나 CP3-C1 기능 결함의 증거는 확인되지 않았다.
- 현재 대응: scanner source, threshold, filter, scope를 변경하지 않는다. self-report의 exact entropy 설명은 GPT가 독립적으로 검증하지 않았으며 확립된 원인으로 기록하지 않는다. 근본 원인은 미검증 상태로 별도 QA infrastructure 조사에 이월한다.

## KI-015 — CP3-C2-B2-C WebAuthn enrollment/credential-operation schema gap

- 상태:
  `OPEN — ADR-015 PROPOSED / SCHEMA REMEDIATION AWAITING GPT INDEPENDENT REVIEW`
- 관찰: CP3-C2-B2-C implementation-entry audit에서 frozen `0005`가 valid
  credential 이전의 server-created SID-bound first-enrollment bootstrap,
  WebAuthn create challenge, expiry와 실패 포함 unique terminal consumption을
  관계형으로 표현하지 못한다. Existing `reviewer_authentication_events`는
  issuer decision/bundle/disposition에 강제 결합되어 credential add/replace
  fresh assertion과 그 counter advancement를 credential-operation authority로
  기록할 수 없다.
- 영향: Windows Hello enrollment, credential lifecycle authorization과 human
  issuer approval runtime은 구현을 시작할 수 없다. `payload_json`, process/
  browser memory, fake issuer challenge, synthetic credential 또는
  unauthenticated recovery로 우회하면 accepted B1/ADR-014 trust root를
  위반한다.
- 현재 대응:
  `plans/PHASE_02_CP3_C2_B2_C_SCHEMA_REMEDIATION.md`와 ADR-015가 table rebuild
  없는 additive future `0006` operation/challenge/consumption/authentication/
  authorization/outcome ledger를 제안한다. ADR-015는 `PROPOSED`이고 `0006`
  creation/application 및 B2-C runtime은 `0`이다. GPT independent review와
  explicit user acceptance 전에는 B2-C를 재개하지 않는다.
- 비차단 정정: issuer `SUPERSEDED`는 현재 schema blocker가 아니다. Existing
  `0005`의 separate authenticated events와 linear link history로 atomic old
  supersession/successor approval/head CAS를 표현할 수 있다.

## KI-010 — Windows non-ASCII 개발·QA 저장소 경로의 editable install 실패

- 상태: `P2 DEFERRED — ENVIRONMENT CONSTRAINT`
- 관찰: Windows의 non-ASCII parent path에서 Python 3.13.15 + setuptools editable install 중 경로가 손상되어 wheel build가 실패했다. 동일 commit을 ASCII-only 경로 `C:\Users\beomoo\Documents\ChatGPT\tosstoss`에 clean clone한 뒤 `scripts/setup.ps1`과 전체 `scripts/test.ps1`이 통과했다.
- 영향: 현재 Windows 개발·QA repository path는 ASCII-only 사용을 권장하며, 재현 가능한 setup portability 제약이다. Toss runtime·OAuth·rate-limit·business logic에 영향을 준 증거는 없다.
- 현재 대응: ASCII-only clone path를 사용한다. CP2 completion blocker나 unresolved functional defect로 보지 않고, 향후 setup portability hardening 후보로 이월한다.
