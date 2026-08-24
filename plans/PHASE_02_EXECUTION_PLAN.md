# Phase 2 토스증권 읽기 전용 데이터 실행계획

- 계획 상태: `PHASE 2 IMPLEMENTATION IN PROGRESS`
- Current checkpoint: `CP3-A REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
- 최초 작성·공식 문서 조사일: `2026-08-23` (`Asia/Seoul`)
- 현재 상태 갱신일: `2026-08-25` (`Asia/Seoul`)
- 기준 브랜치: `feature/phase-02-toss`
- CP3-A 시작 commit: `6bd5d2ae9c26f02f2cd4bd75a474633a9082fa16`
- Remote main/merge-base: `353159da45cfbe3a7f444bf476ce86fa9aece17c`
- Phase 1 baseline: `v0.1.0` → `b1829a7375704271a21267e1fcf62808147be593`

이 문서는 Phase 2의 구현 계약이다. checkpoint 완료를 다음 checkpoint의 승인으로 확대하지 않는다.
공식 문서와 실응답이 다르면 실응답을 조용히 수용하지 않고 수집을 중단한 뒤 문서·fixture·계약을 함께 재검토한다.

## Current execution status

- Phase 1: `COMPLETE`, release baseline `v0.1.0`
- CP1: `PASS`
- CP2: `COMPLETE`
- CP3-A: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
- CP3-B: `NOT STARTED`
- Phase 2: `IMPLEMENTATION IN PROGRESS`

CP3-A는 `plans/PHASE_02_CP3_A_CONTRACT.md`를 중심으로 Security Master와 Current Price의 계획·계약만 작성하는 documentation checkpoint다. 첫 독립검증은 `CHANGES REQUIRED`(P0 0/P1 2)였고 provider-scoped price/canonical view 분리와 immutable provider identity reconciliation을 보완했다. application, test, fixture, migration, dependency, runtime config, API route와 collection job은 변경하지 않는다. GPT 재검토와 사용자 승인 전에는 CP3-A를 `PASS`, `APPROVED` 또는 `COMPLETE`로 표시하지 않고 CP3-B를 시작하지 않는다.

## Original CP1 investigation baseline

2026-08-23 CP1 당시에는 credential을 요청·사용하지 않았고 실제 Toss endpoint 호출도 없었다. 따라서 당시 조사 결과는 전부 공식 공개 계약에 근거한 `[OFFICIAL_DOC]`/`[LIVE_UNVERIFIED]`였고 `[LIVE_VERIFIED]` 항목은 없었다. 아래 source hash, endpoint/field/rate/finality 조사 표는 그 역사적 CP1 기준을 보존한다. 현재 live 상태를 2026-08-23부터 검증됐던 것처럼 소급하지 않는다.

## Current live verification matrix

| 대상 | current status | 확인 범위 | 확대 금지 범위 |
|---|---|---|---|
| canonical provider contract | `[LIVE_VERIFIED]` | origin/hash 일치, OpenAPI `3.1.0`, provider REST `1.2.14`, drift 없음 | 이후 version/hash가 영구 고정됐다는 주장 |
| OAuth | `[LIVE_VERIFIED]` | actual token issuance, credential acceptance, allowed-IP execution path | token body/value/TTL의 모든 edge semantics |
| `GET /api/v1/stocks` | `[LIVE_VERIFIED]` | actual endpoint 호출과 성공 outer response structure | 전체 market·enum·nullable field·identifier/lifecycle semantics |
| 성공 rate headers | `[LIVE_VERIFIED]` | stocks 성공 응답의 Limit/Remaining/Reset 유효성 | `Retry-After`, natural 429, 다른 group/endpoint behavior |
| `GET /api/v1/stocks/all` | `[LIVE_UNVERIFIED]` | 공식 contract만 조사 | universe 완전성, enum/null/lifecycle semantics |
| `GET /api/v1/prices` | `[LIVE_UNVERIFIED]` | 공식 contract만 조사 | price/currency/timestamp-null/freshness semantics |
| 나머지 market endpoint | `[LIVE_UNVERIFIED]` | 공식 contract만 조사 | 실제 body/header/timing/finality |
| 429/5xx와 production timing | `[LIVE_UNVERIFIED]` | offline MockTransport/fake-time contract만 검증 | actual provider retry timing과 `Retry-After` |

## Current checkpoint status

CP3-A는 기존 Phase 1 계약을 breaking 변경하지 않고 provider staging identity, nullable provider source time, raw/source revision, provider-scoped current latest와 additive migration 승인안을 정의한다. valid provider identity의 price storage는 canonical issuer/security mapping과 분리하고 canonical current-price view만 verified linkage를 요구한다. identity allocation은 continuity-first reconciliation 뒤 신규 anchor를 선택하며 enrichment가 ID를 rekey하지 않는다. ADR-011은 사용자 승인을, revised ADR-012는 GPT 재검토와 사용자 결정을 기다린다. CP3-B/C/D의 application work는 아직 시작하지 않았다.

## Historical checkpoint record

| checkpoint | historical result | 비고 |
|---|---|---|
| CP1 | `PASS` | 공식 계약 조사와 실행계획; 당시 live 검증 0 |
| CP2-A | `PASS` | Toss-only dependency/config/policy boundary |
| CP2-B | `PASS` | OAuth/token manager/exact HTTP boundary와 P2 hardening |
| CP2-C | `PASS` | rate/retry/error taxonomy와 cumulative-wait hardening |
| CP2-D1 | `PASS` | safe live preflight tooling의 offline validation |
| CP2-D2 | `PASS` | 승인된 actual OAuth/stocks one-shot 최소 검증 |
| CP2 | `COMPLETE` | final integrated QA; Phase 2 전체 완료 아님 |
| CP3-A | `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW` | P1-01/P1-02 문서 보완만; application implementation 0 |
| CP3-B | `NOT STARTED` | 자동 진입 금지 |

## 0. 근거 분류

| 표기 | 의미 |
|---|---|
| `[OFFICIAL_DOC]` | 2026-08-23에 확인한 토스증권 공식 개발자 문서·OpenAPI·AsyncAPI에 명시됨 |
| `[LIVE_VERIFIED]` | 허용 IP와 실제 credential을 사용한 실 API 응답으로 확인됨 |
| `[REPO_CONTRACT]` | 이 저장소의 승인된 문서·계약·보안 정책에 명시됨 |
| `[LIVE_UNVERIFIED]` | 공개 계약은 있으나 credential·허용 IP가 필요한 실응답 검증은 아직 하지 않음 |
| `[UNVERIFIED]` | 공식 문서와 실응답 어디에서도 확인되지 않음. 구현 기본값으로 사용 금지 |

CP1 조사 시점에는 `[LIVE_VERIFIED]` 항목이 없었다. 현재 상태는 위 `Current live verification matrix`를 따른다.

## 1. 목표

Phase 2는 토스증권 Open API의 **계좌와 무관한 읽기 전용 시장 데이터**만 백엔드에서 수집한다.

1. OAuth 2.0 Client Credentials 방식의 서버 전용 토큰 관리
2. 종목 유니버스와 종목 마스터
3. 현재가
4. 1분봉·일봉
5. 국내 종목의 투자자별 수급, 프로그램매매, 공매도, 신용거래, 대차거래
6. 공식 장 운영일을 사용한 안전한 polling·freshness 보조
7. 원문 → 정규화 → 분석 저장소 추적성과 멱등성
8. 호출 한도, 인증·권한·일시 오류, 부분 실패와 데이터 품질 상태

Phase 2는 투자 주문 시스템이 아니며, 외부 API 응답을 도메인 판단이나 투자 신호로 해석하지 않는다.

## 2. 공식 source 목록과 확인일

확인일은 모두 `2026-08-23`이다. canonical JSON/Markdown을 대화형 UI보다 우선한다.

| 우선순위 | source | 확인 결과 | SHA-256 |
|---:|---|---|---|
| 1 | [Canonical OpenAPI JSON](https://openapi.tossinvest.com/openapi-docs/latest/openapi.json) | REST endpoint·schema·error·rate group source of truth | `fccf49abd11f37f557bdd349138f4a03c42b829ebd8b5c14ab4907116fb84c7a` |
| 2 | [Canonical AsyncAPI JSON](https://openapi.tossinvest.com/openapi-docs/latest/asyncapi.json) | WebSocket channel source of truth | `130251057fd9535a3e276099f9166b445f8c51f505f30540758e4b209231282e` |
| 3 | [공식 overview](https://openapi.tossinvest.com/openapi-docs/overview.md) | 시작 절차, rate limit 표, 오류·WebSocket 운영 설명 | `dfad8c9251917daf39d2b2a9e455f0d7cadddafb42a34f47b2ee8d67bf4addd8` |
| 4 | [공식 Markdown reference](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/README.md) | AI·비 JavaScript용 reference | `30c0532c1cc4010d1d7ec0878cbb0a1c2cfd291d104eb4e3cc99683d7f8da0f5` |
| 5 | [개발자 안내 llms.txt](https://developers.tossinvest.com/llms.txt) | canonical source 위치와 API coverage 안내 | `a57be4baa04d60b68897b2766802bd626b9c88d7fcea1c5306d2318cb36a9988` |
| 6 | [대화형 개발자 문서](https://developers.tossinvest.com/docs) | 사람이 읽는 UI; canonical schema와 충돌하면 하위 우선순위 | N/A |

공식 문서 snapshot은 저장소에 복제하지 않는다. 위 hash는 확인 시점의 drift 식별용이며 영구 계약값이 아니다.

## 3. 공식 API version

- `[OFFICIAL_DOC]` REST 문서: OpenAPI `3.1.0`, `info.version = 1.2.14`
- `[OFFICIAL_DOC]` REST base server: `https://openapi.tossinvest.com`
- `[OFFICIAL_DOC]` WebSocket 문서: AsyncAPI `3.0.0`, `info.version = 1.2.2`
- `[OFFICIAL_DOC]` WebSocket server: `wss://openapi-ws.tossinvest.com/ws/v1`
- `[REPO_CONTRACT]` Phase 2 callable transport: **REST only**

Provider API version과 내부 `contract_version`은 별개다. 기존 Phase 1 공개 계약은 `0.1.0`을 유지한다.
Phase 2에서 기존 schema를 호환 불가능하게 바꿔야 하면 전역 Literal을 넓히지 않고 새 versioned contract와 migration을 별도 승인한다.

## 4. Phase 2 포함 범위

### 4.1 callable allowlist

아래 12개 method/path tuple만 Phase 2 runtime에서 호출할 수 있다.

```text
POST /oauth2/token
GET  /api/v1/stocks
GET  /api/v1/stocks/all
GET  /api/v1/prices
GET  /api/v1/candles
GET  /api/v1/stocks/{symbol}/investor-trading
GET  /api/v1/stocks/{symbol}/program-trades
GET  /api/v1/stocks/{symbol}/short-selling
GET  /api/v1/stocks/{symbol}/credit-trades
GET  /api/v1/stocks/{symbol}/securities-lending
GET  /api/v1/market-calendar/KR
GET  /api/v1/market-calendar/US
```

`/api/v1/stocks/all`은 전체 종목 유니버스 구성에 필요하고, 두 market calendar는 장중 polling과 date/finality 판단 보조에만 사용한다.

### 4.2 조사 완료·호출 보류 support endpoint

다음 5개 endpoint는 공식 계약을 확인했지만 Master Plan의 Phase 2 필수 범위를 넓히지 않기 위해 callable allowlist에는 넣지 않는다.

```text
GET /api/v1/stocks/{symbol}/warnings
GET /api/v1/exchange-rate
GET /api/v1/market-indicators/prices
GET /api/v1/market-indicators/{symbol}/candles
GET /api/v1/market-indicators/{symbol}/investor-trading
```

이 endpoint를 추가하려면 사용 목적, 저장 계약, 테스트와 rate budget을 본 계획에 반영한 후 다시 승인한다.

## 5. 명시적 비범위

- 모든 계좌·자산·주문·조건주문 endpoint
- `/api/v1/accounts`, `/api/v1/holdings`
- `/api/v1/orders`와 주문 생성·정정·취소·조회
- `/api/v1/buying-power`, `/api/v1/sellable-quantity`, `/api/v1/commissions`
- `/api/v1/conditional-orders` 전체
- `X-Tossinvest-Account` header와 계좌 식별 설정
- WebSocket 연결·구독·주문 이벤트
- 호가, 최근 체결, 상·하한가, 랭킹
- OpenDART, SEC/13F, 뉴스, 매크로, OpenAI API
- 실제 주문·모의주문·자동매매
- Phase 5의 본격 dashboard 화면
- 비공식 scraping과 유료 API

금지 endpoint는 존재 여부만 문서로 확인했으며 호출하지 않는다.

## 6. endpoint contract matrix

### 6.1 요청·paging·rate matrix

모든 행의 request/paging/rate source class는 CP1의 `[OFFICIAL_DOC]` 조사다. 현재 live 상태는 다음 표로 별도 관리하며, 실제 확인한 좁은 범위를 endpoint 전체 semantics 검증으로 확대하지 않는다.

| method / endpoint | current live status | exact scope |
|---|---|---|
| `POST /oauth2/token` | `[LIVE_VERIFIED]` | actual issuance, credential acceptance, allowed-IP path; body/value/edge semantics 저장·확대 금지 |
| `GET /api/v1/stocks` | `[LIVE_VERIFIED]` | actual call과 성공 outer response; 전체 enum/null/market semantics는 `[LIVE_UNVERIFIED]` |
| `GET /api/v1/stocks/all` | `[LIVE_UNVERIFIED]` | 공식 contract only |
| `GET /api/v1/prices` | `[LIVE_UNVERIFIED]` | 공식 contract only |
| `GET /api/v1/candles` | `[LIVE_UNVERIFIED]` | 공식 contract only |
| five KR stock-trend endpoints | `[LIVE_UNVERIFIED]` | 공식 contract only |
| KR/US market calendar | `[LIVE_UNVERIFIED]` | 공식 contract only |
| five support/call-hold endpoints | `[LIVE_UNVERIFIED]` | 공식 contract only, callable allowlist 밖 |

성공 `GET /api/v1/stocks`의 Limit/Remaining/Reset header는 `[LIVE_VERIFIED]`다. natural 429 `Retry-After`, actual 429/5xx, production retry timing과 다른 endpoint rate behavior는 `[LIVE_UNVERIFIED]`다.

| # | method / endpoint | market | request parameters | paging / maximum | rate group | documented TPS |
|---:|---|---|---|---|---|---:|
| 1 | `POST /oauth2/token` | N/A | form: `grant_type`, `client_id`, `client_secret` | 없음 | `AUTH` | 5 |
| 2 | `GET /api/v1/stocks` | KR·US | query `symbols`, 쉼표 구분 | 1~200 symbols, pagination 없음 | `STOCK` | 5 |
| 3 | `GET /api/v1/stocks/all` | KR·US | `market` 필수, `status=ACTIVE`, `securityType`, `commonShare` | pagination 없음, market당 최대 수천 건 | `STOCK_ALL` | 1 |
| 4 | `GET /api/v1/prices` | KR·US | query `symbols` | 1~200 symbols, pagination 없음 | `MARKET_DATA` | 15 |
| 5 | `GET /api/v1/candles` | KR·US | `symbol`, `interval=1m|1d`, `count=100`, `before`, `adjusted=true` | 1~200 bars, `nextBefore` | `MARKET_DATA_CHART` | 20 |
| 6 | `GET /api/v1/stocks/{symbol}/investor-trading` | KR only | path `symbol`, `count=10`, `until` inclusive date | 1~100 records, `nextUntil` | `STOCK_TRADING_TREND` | 10 |
| 7 | `GET /api/v1/stocks/{symbol}/program-trades` | KR only | path `symbol`, `count=10`, `until` inclusive date | 1~100 records, `nextUntil` | `STOCK_TRADING_TREND` | 10 |
| 8 | `GET /api/v1/stocks/{symbol}/short-selling` | KR only | path `symbol`, `count=10`, `until` inclusive date | 1~100 records, `nextUntil` | `STOCK_TRADING_TREND` | 10 |
| 9 | `GET /api/v1/stocks/{symbol}/credit-trades` | KR only | path `symbol`, `count=10`, `until` inclusive date | 1~100 records, `nextUntil` | `STOCK_TRADING_TREND` | 10 |
| 10 | `GET /api/v1/stocks/{symbol}/securities-lending` | KR only | path `symbol`, `count=10`, `until` inclusive date | 1~100 records, `nextUntil` | `STOCK_TRADING_TREND` | 10 |
| 11 | `GET /api/v1/market-calendar/KR` | KR | optional `date` | 전일·당일·익일 3영업일 | `MARKET_INFO` | 3 |
| 12 | `GET /api/v1/market-calendar/US` | US | optional local `date` | 전일·당일·익일 3영업일 | `MARKET_INFO` | 3 |
| 13 | `GET /api/v1/stocks/{symbol}/warnings` | KR·US | path `symbol` | active warnings 전체, pagination 없음 | `STOCK` | 5 |
| 14 | `GET /api/v1/exchange-rate` | KRW·USD | optional `dateTime`, required `baseCurrency`, `quoteCurrency` | 단건 | `MARKET_INFO` | 3 |
| 15 | `GET /api/v1/market-indicators/prices` | KR indicators | `symbols`, 최대 200 | pagination 없음 | `MARKET_INDICATOR` | 10 |
| 16 | `GET /api/v1/market-indicators/{symbol}/candles` | KR indicators | `symbol`, `interval`, `count`, `before` | 1~200 bars, `nextBefore` | `MARKET_INDICATOR_CHART` | 5 |
| 17 | `GET /api/v1/market-indicators/{symbol}/investor-trading` | KOSPI·KOSDAQ | `symbol`, `interval=1d|1w|1mo|1y`, `count`, `until` | 1~100 records, `nextUntil` | `MARKET_INDICATOR` | 10 |

`MARKET_INDICATOR_PRICE` group은 공식 rate 표에 존재하지만 v1.2.14의 위 scoped operation description에는 매핑되지 않았다. 임의로 사용하지 않는다.

### 6.2 response field·type matrix

| endpoint | 주요 response fields | Decimal string | JSON integer / boolean | currency | null semantics |
|---|---|---|---|---|---|
| token | `access_token`, `token_type=Bearer`, `expires_in` | 없음 | `expires_in` integer | N/A | 필수 3필드; refresh token 없음 |
| stocks | `symbol`, `name`, `englishName`, `isinCode`, `market`, `securityType`, `isCommonShare`, `status`, `currency`, `listDate`, `delistDate`, `sharesOutstanding`, `leverageFactor`, `koreanMarketDetail` | `sharesOutstanding`, `leverageFactor` | share/status detail boolean | response field | 미제공 상장일, 활성 종목 폐지일, 비 ETF leverage, 해외 detail은 null |
| stocks/all | `symbol`, `name`, `securityType`, `isCommonShare`, `isinCode` | 없음 | `isCommonShare` boolean | 상세 조회에서 보강 | 공식 schema 필수 필드만 반환 |
| prices | `symbol`, `timestamp`, `lastPrice`, `currency` | `lastPrice` | 없음 | response field | 체결 미발생 등 시 `timestamp=null`; 가격은 필수 |
| candles | `candles[]`, `nextBefore`; item: `timestamp`, `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, `currency` | OHLCV 전부 | 없음 | response field | 마지막 페이지 `nextBefore=null`; 빈 목록 가능 |
| investor-trading | `date`, `updatedAt`, `individual`, `foreigner`, `institution`, `otherCorporation`, `foreignerHolding`, `cfd`; buy/sell/net volume과 기관 7개 breakdown | 모든 수량·비율 | 없음 | 수량만 제공 | 당일 `individual`, breakdown, 기타법인, 보유, CFD가 null일 수 있음 |
| program-trades | `date`, `arbitrage`, `nonArbitrage`; 각 buy/sell/net volume | 모든 수량 | 없음 | 수량만 제공 | 빈 records와 마지막 `nextUntil=null`; item field는 필수 |
| short-selling | `date`, `updatedAt`, `shortSellingVolume`, `shortSellingAmount`, 두 rate | 수량·금액·비율 | 없음 | amount는 암묵적 KRW | 분모 자료 부재 시 rate null, 분모 0이면 문자열 `0` |
| credit-trades | `date`, `updatedAt`, `marginLoan`, `stockLoan`; new/return/balance quantity, balance/trading rate | 모든 수량·비율 | 없음 | 수량·비율 | 한쪽 데이터 부재 시 해당 object null |
| securities-lending | `date`, `updatedAt`, execution/repayment/balance quantity, `balanceAmount` | 모든 수량·금액 | 없음 | amount는 암묵적 KRW | 빈 records와 마지막 `nextUntil=null` |
| KR calendar | `today`, `previousBusinessDay`, `nextBusinessDay`; date와 nullable integrated session | 없음 | 없음 | N/A | KRX·NXT 모두 휴장 시 session null |
| US calendar | 동일 3영업일; `dayMarket`, `preMarket`, `regularMarket`, `afterMarket` | 없음 | 없음 | N/A | 휴장 세션은 null; date는 미국 현지 date |
| warnings | `warningType`, `exchange`, `startDate`, `endDate` | 없음 | 없음 | N/A | 거래소 무관·미정 날짜는 null; 경고 없음은 `result=[]` |
| exchange-rate | `baseCurrency`, `quoteCurrency`, `rate`, `midRate`, `basisPoint`, `rateChangeType`, `validFrom`, `validUntil` | rate 3종 | 없음 | response fields | schema상 필수 |
| indicator prices | `symbol`, `timestamp`, `lastPrice` | `lastPrice` | 없음 | symbol catalog로 해석 | 데이터 미제공 시 timestamp null |
| indicator candles | timestamp, OHLCV, nextBefore | OHLCV | 없음 | symbol catalog로 해석 | 마지막 nextBefore null |
| indicator investor | date, updatedAt, 4분류 buy/sell amount와 기관 breakdown | 모든 금액 | 없음 | 암묵적 KRW | 빈 records, 마지막 nextUntil null |

`format: decimal`인 문자열은 JSON number나 binary float으로 변환하지 않는다. 수량이 정수 의미여도 canonical Decimal string으로 보존하고 정수 제약을 별도 검증한다.

### 6.3 freshness·finality·revision matrix

| dataset | 공식 적시성 | Phase 2 finality 기본 규칙 | possible revision |
|---|---|---|---|
| stock master | `/stocks/all` 일 배치, 하루 1회 cache 권장 | `UNKNOWN` | listing/status/master 변경 가능; hash 변화 보존 |
| current price | 실시간성 시세, 정확한 latency 미명시 | `UNKNOWN` | snapshot 누적, 과거 덮어쓰기 금지 |
| candles | 1m·1d 제공; 확정 시각 미명시 | `UNKNOWN` | adjusted 요청과 기업행사 재산출 가능성을 live 확인 전 추측하지 않음 |
| investor trading | 당일 장중 잠정; 수급 확정치는 저녁, CFD T+1 새벽, 외국인 보유 T+1 오전 재갱신 가능 | same-day/incomplete는 `PRELIMINARY`; 명시적 observable 확정 규칙을 live 검증하기 전 나머지는 `UNKNOWN` | `updatedAt`·content hash 변화마다 version 보존 |
| program trades | 당일 기록은 장 종료 전까지 갱신 가능 | same-day는 `PRELIMINARY`; 과거는 명시적 final 신호가 없어 `UNKNOWN` | 같은 자연키 hash 변화 보존 |
| short selling | 일별 확정치가 당일 저녁 반영 | 반환 시각만으로 단정하지 않고 CP5 live rule 승인 전 `UNKNOWN` | `updatedAt`·hash 변화 보존 |
| credit trades | T+1 새벽 반영, 최신 기록은 전 영업일 | `UNKNOWN` | `updatedAt`·hash 변화 보존 |
| securities lending | 일별 확정치가 당일 저녁 반영 | CP5 live rule 승인 전 `UNKNOWN` | `updatedAt`·hash 변화 보존 |
| market calendars | 조회 기준 3영업일, KST 표시 | N/A | 일정 변경 시 raw/version 보존 |
| warnings | VI 수 초, 지정정보 일 배치 | active snapshot, `UNKNOWN` | 활성 목록 변화 보존 |
| exchange rate | 1분 갱신, `validFrom`~`validUntil` | 유효 window로 freshness 평가, finality `UNKNOWN` | 같은 window hash 변화 보존 |
| market indicators | 당일 수급은 장 종료 전까지 잠정 | same-day `PRELIMINARY`, 그 외 `UNKNOWN` | `updatedAt`·hash 변화 보존 |

장 종료 여부만으로 `FINAL`을 만들지 않는다. 공식 문서가 “확정치”라고 설명해도 API가 명시적 final flag를 주지 않으므로 live sample에서 deterministic 전환 조건을 확인하고 계획을 갱신하기 전에는 `UNKNOWN`을 유지한다.

### 6.4 known errors

- token endpoint: OAuth 형식의 `invalid_request`, `unsupported_grant_type`, `invalid_client`, `access_denied`, 429
- protected API 공통: 401 `invalid-token`, `expired-token`, `login-user-not-found`; Authorization 누락 시 `edge-blocked`
- 403: 허용 IP 또는 권한 문제의 `edge-blocked` / `forbidden`
- 400: `invalid-request`, KR-only endpoint의 `unsupported-market`, indicator의 `unsupported-symbol`
- 404: `stock-not-found`, `exchange-rate-not-found` 등 endpoint별 not found
- 429: `edge-rate-limit-exceeded` 또는 `rate-limit-exceeded`
- 500: `internal-error`, `maintenance` 등 일시 장애
- 성공은 `result`, 오류는 `error.requestId`, `error.code`, `error.message`, optional `error.data` envelope이다. token endpoint만 OAuth 표준 오류 envelope를 사용한다.
- unknown error code와 enum은 파싱 실패로 전체 과거 데이터를 삭제하지 않고 raw 보존 + dataset `DEGRADED`/`ERROR`로 격리한다.

## 7. auth/token contract

### 7.1 공식 계약

- `[OFFICIAL_DOC]` grant: OAuth 2.0 Client Credentials Grant
- `[OFFICIAL_DOC]` endpoint: `POST https://openapi.tossinvest.com/oauth2/token`
- `[OFFICIAL_DOC]` content type: `application/x-www-form-urlencoded`
- `[OFFICIAL_DOC]` required fields: `grant_type=client_credentials`, `client_id`, `client_secret`
- `[OFFICIAL_DOC]` response: `access_token`, `token_type=Bearer`, `expires_in` seconds
- `[OFFICIAL_DOC]` refresh token은 제공하지 않는다. 만료 시 동일 endpoint로 재발급한다.
- `[OFFICIAL_DOC]` client당 유효 access token은 하나이며 재발급 시 이전 token은 즉시 무효화된다.
- `[OFFICIAL_DOC]` 등록된 허용 IP 밖의 호출은 403이다.
- `[OFFICIAL_DOC]` 시장 데이터는 `Authorization: Bearer`만 필요하다.
- `[REPO_CONTRACT]` `X-Tossinvest-Account`는 Phase 2 config·client·request model에 존재하지 않는다.

`expires_in: 86400`은 공식 example이지 영구 TTL 상수가 아니다. runtime response 값을 사용하며 코드 기본값을 두지 않는다.

### 7.2 token manager

- 백엔드 프로세스당 단일 token manager
- async single-flight lock으로 동시에 하나의 발급·재발급만 허용
- token과 계산된 expiry는 memory-only
- expiry 판단은 wall clock 표시와 분리해 monotonic clock을 사용
- 발급 응답의 `expires_in`이 양의 정수가 아니면 token을 폐기하고 fail closed
- refresh token 로직 없음
- 401 `expired-token` 또는 `invalid-token`에서 단 한 번 강제 재발급 후 원 요청을 한 번만 replay
- 400/401 `invalid_client`, 403 IP/permission은 자동 반복하지 않고 `BLOCKED`
- 프로세스 재시작 시 환경변수 credential로 새 token을 발급하며 DB에서 복원하지 않음

## 8. rate-limit contract

### 8.1 scoped group

Phase 2가 확인한 rate group은 9개다.

```text
AUTH=5 TPS
STOCK=5 TPS
STOCK_ALL=1 TPS
STOCK_TRADING_TREND=10 TPS
MARKET_INFO=3 TPS
MARKET_DATA=15 TPS
MARKET_DATA_CHART=20 TPS
MARKET_INDICATOR=10 TPS          # support endpoint, 호출 보류
MARKET_INDICATOR_CHART=5 TPS    # support endpoint, 호출 보류
```

문서 수치는 versioned metadata인 `documented_limit`일 뿐 영구 상수가 아니다.

### 8.2 runtime 운영값

- `documented_limit`: 확인한 공식 문서 수치
- `observed_limit`: 최신 정상·429 응답의 `X-RateLimit-Limit`
- `effective_limit`: configured ceiling과 유효한 observed limit 중 더 보수적인 값
- 응답마다 `X-RateLimit-Remaining`, `X-RateLimit-Reset`을 관찰해 group별 bucket을 갱신
- header가 없거나 파싱 불가하면 documented ceiling을 높이지 않고 `RATE_LIMIT_HEADERS_MISSING` quality flag 기록
- credential·token과 달리 숫자형 rate telemetry는 SQLite job/status metadata에 저장 가능
- client × group 단위 limiter를 공유하여 job별 limiter 중복을 금지

### 8.3 429

- `Retry-After`를 최우선한다.
- 전체 시도는 최초 요청 포함 최대 3회다.
- `Retry-After`가 30초 이하이면 bounded delay + jitter 후 재시도한다.
- 30초 초과, 누락·비정상 값, retry budget 소진 시 프로세스를 오래 sleep하지 않고 job을 `RETRYING`으로 reschedule한다.
- 무한 retry와 rate group 간 budget 공유를 금지한다.

## 9. retry/error taxonomy

| 분류 | 예 | 동작 |
|---|---|---|
| success | 2xx + valid schema | raw 저장 후 normalize |
| contract error | 2xx지만 schema 불일치 | raw 보존, normalize 금지, dataset `DEGRADED`, 자동 반복 없음 |
| request error | 400, unsupported market/symbol | 잘못된 item 격리, 자동 retry 없음 |
| auth refreshable | 401 expired/invalid token | single-flight 재발급 1회 + 원 요청 replay 1회 |
| auth blocked | invalid client, 403, 허용 IP | credential 출력 없이 `BLOCKED`, retry 없음 |
| not found | 404 | 해당 symbol `UNAVAILABLE`; master 재확인 전 0/빈값 생성 금지 |
| throttled | 429 | `Retry-After` 우선, bounded retry/reschedule |
| transient | 500, maintenance, timeout, connection reset | 1s→2s bounded exponential backoff + full jitter, 전체 3회 |
| TLS/DNS/security | 인증서 검증, host mismatch | 즉시 fail closed, retry로 우회 금지 |

같은 자연키의 마지막 검증 데이터는 실패 시 삭제하지 않는다. 새 raw가 검증 실패하면 publish 단계로 진행하지 않는다.

## 10. security boundary

### 10.1 network

- backend connector만 `https://openapi.tossinvest.com:443`에 접근
- redirects 비활성 또는 같은 origin의 안전한 GET만 명시적으로 허용; cross-origin redirect 금지
- TLS 검증 해제 금지
- proxy 환경변수 상속 여부를 CP2에서 fail-closed 검증
- browser·Next.js bundle은 Toss host에 접근하지 않음
- standard test는 non-loopback outbound를 계속 차단
- live test는 별도 명시적 command와 environment gate에서만 수행

### 10.2 forbidden API fail-closed

`scripts/policy-scan.ps1`을 Phase 2 deny-by-default 정책으로 확장한다.

- exact method/path allowlist만 허용
- runtime source의 `/accounts`, `/holdings`, `/orders`, `/buying-power`, `/sellable-quantity`, `/commissions`, `/conditional-orders` 거부
- `X-Tossinvest-Account` 문자열·config·header 구성 거부
- POST는 `/oauth2/token`만 허용
- `openapi-ws.tossinvest.com`, `ws://`, `wss://` runtime 사용 거부
- OpenAI/provider package와 order/trade execution pattern 기존 canary 유지
- 새 connector directory는 `services/api/src/toss_dashboard_api/connectors/toss`만 허용

### 10.3 Phase 1 변경이 필요한 이유와 비완화 조건

현재 `test_no_external_network.py`는 모든 HTTP client import와 connector directory를 금지한다. CP2에서 실제 Toss read-only 연결을 위해 다음처럼 **범위를 좁혀 변경**한다.

- blanket import 금지를 “승인된 Toss connector 밖의 HTTP client import 금지”로 변경
- `httpx` runtime dependency는 exact version·lock·공식 PyPI hash 정책을 통과해야 함
- pytest 기본 실행의 socket 차단은 유지
- `MockTransport` 기반 offline test와 exact-host transport test를 추가
- forbidden endpoint/header negative canary를 늘려 외부 연결 허용이 계좌·주문 허용으로 번지지 않게 함

Phase 1 테스트 삭제, skip, xfail, inventory 감소는 허용하지 않는다.

## 11. raw/normalized storage design

### 11.1 Raw Source

- market-data 응답 body를 append-only 파일로 보존
- 인증 token 응답과 token endpoint request body는 raw 저장 대상에서 제외
- request metadata에는 method, allowlisted path, secret 없는 canonical query, fetch 시각만 저장
- response metadata에는 status, `X-Request-Id`, rate header, content type만 allowlist 저장
- Authorization, cookie, client ID/secret, access token, account header는 저장 금지
- raw bytes SHA-256을 계산하고 temp file → fsync 가능한 범위 → atomic rename 후 manifest publish
- 동일 request 자연키와 payload hash 재수집은 새 audit event를 남기되 normalized duplicate를 만들지 않음
- `raw_storage_ref`는 로컬 opaque ref만 노출하고 절대경로와 credential을 포함하지 않음

### 11.2 Normalized

- 기존 `Issuer` / `Security` 분리를 유지
- `SourceSystem.TOSS_OPEN_API`와 필요한 source type을 명시적으로 추가
- 종목 master는 provider identifier history를 continuity-first로 reconciliation하고 최초 allocation 뒤 immutable `provider_security_identity_id`를 사용한다. 신규 anchor는 continuity evidence가 0일 때만 ISIN → symbol+listDate → symbol+first-seen raw evidence 순으로 선택하며, enrichment는 rekey하지 않는다.
- 현재가는 provider identity 기준 `ProviderPriceSnapshot`과 provider latest를 사용하고 nullable canonical `security_id` linkage와 분리한다. canonical current-price view는 verified linkage에서만 노출한다. candles는 확장된 `PriceBar`, 수급은 dataset별 normalized contract로 분리한다.
- provider의 camelCase field 이름·원문 enum은 raw에 보존하고 normalizer가 내부 enum으로 명시적으로 매핑
- unknown enum은 임의 매핑하지 않고 record reject + raw 보존
- 모든 normalized row에 `source_record_id`, normalized hash, contract version, freshness/finality/revision을 유지

### 11.3 날짜 전용 source contract

기존 Phase 1 `SourceRecord`는 `observed_at`·`published_at`을 필수 datetime으로 요구하지만 일부 Toss 수급 응답은 `date`만 제공하고 publication timestamp를 제공하지 않는다. 날짜를 자정 timestamp로 만들거나 `fetched_at`을 `observed_at`으로 복사하지 않는다.

CP3-B 승인 후 versioned provider source contract를 추가하는 방안을 제안한다. CP3-A에서는 문서만 작성한다.

- 기존 Phase 1 `SourceRecord`와 fixture는 변경 없이 계속 유효
- 새 contract는 nullable `observed_at`과 nullable `observed_date`를 구분
- 둘 다 null인 상태를 허용하되 각각의 structured missing reason 필수
- 둘 다 값이 있으면 dataset contract가 허용하는 조합인지 검증
- nullable `published_at`이 null이면 structured missing reason 필수
- `fetched_at`은 required aware UTC이며 observed/published time을 대신하지 않음
- 전역 `ContractVersion` 허용 범위를 무조건 넓히지 않음
- 새 provider source contract에 독립 version 부여
- 기존 API·fixture의 `contract_version=0.1.0` 회귀를 유지
- schema 변경안과 migration은 ADR-011 independent review와 사용자 승인 필요

### 11.4 Analytics

- SQLite: provider/canonical security master linkage, source metadata, job/audit/data-quality와 provider identity 기준 latest-state pointer
- Parquet: price/candle/flow append-versioned 시계열
- DuckDB: Parquet query adapter; provider credential·token·raw auth response 저장 금지
- partition 후보: canonical mapping 전에는 `dataset/market/provider_security_identity_id/year/month`, verified canonical projection은 linkage metadata를 사용한다. 최종 파일명은 payload/version hash 포함
- 수정 수집은 기존 파일 덮어쓰기보다 새 version + manifest pointer 갱신
- partially written partition은 publish하지 않음

## 12. timestamp/date/finality 규칙

- provider offset timestamp는 원문을 raw에 보존하고 normalized 값은 aware UTC로 변환
- `timestamp`, `updatedAt`, `validFrom`, `validUntil`은 datetime
- `date`, `listDate`, `delistDate`, `until`은 date-only이며 임의 자정 변환 금지
- KR trade date는 KST calendar date, US calendar date는 공식 설명대로 미국 현지 date
- `fetched_at`은 response body 수신 완료 시점의 UTC
- `observed_at`은 provider가 제공한 데이터 기준 timestamp만 사용
- date-only dataset은 `observed_date`에 저장
- current price의 provider `timestamp=null`은 `observed_at=null`, `observed_date=null`과 structured missing reason으로 표현하고 `fetched_at`을 복사하지 않음
- current price timestamp null의 availability는 `DEGRADED`, freshness는 `UNKNOWN`이며 current/latest pointer를 갱신하지 않음
- freshness 평가는 `fetched_at`과 관측 시간/date, calendar, dataset policy를 분리해 계산
- API가 명시적 finality flag를 주지 않으면 기본 `UNKNOWN`
- 공식 문서로 장중 변경이 확실한 당일 값은 `PRELIMINARY`
- `FINAL` 자동 전환은 live evidence와 deterministic rule 승인 전 금지
- 같은 자연키의 payload hash 변화는 revision history로 보존하고 기존 검증본을 삭제하지 않음

## 13. checkpoint별 구현 계획

### CP1 — 공식 계약 / execution plan (이번 checkpoint)

- 구현 파일: 없음
- 수정 가능한 기존 파일: `DECISIONS.md`, `KNOWN_ISSUES.md`
- 신규 문서: `plans/PHASE_02_EXECUTION_PLAN.md`
- DB migration: 없음
- fixture/package/application source: 없음
- 테스트: `git diff --check`, secret scan, policy scan
- rollback: 문서 commit revert
- 완료 조건: 공식 version·endpoint·rate·오류·보안·저장·checkpoint 계약과 미확인 항목이 문서화되고 commit/push됨

### CP2 — Auth + Toss HTTP client + rate limiter + offline/live boundary

CP2의 범위와 최종 acceptance는 유지하되 구현·검증 순서는 다음 네 단계로 나눈다.

1. **CP2-A — Security Boundary + Dependency + Config + Policy**
2. **CP2-B — OAuth Token Manager + Toss HTTP Client**
3. **CP2-C — Rate Limit + Retry + Error Taxonomy**
4. **CP2-D — Live Preflight + Full Regression QA**

CP2-A의 통과는 CP2 전체 통과가 아니며, 아래 기존 완료 조건은 CP2-D까지 모두 검증한 뒤에만 충족한 것으로 판정한다.

- 구현 파일:
  - `services/api/src/toss_dashboard_api/connectors/toss/auth.py`
  - `services/api/src/toss_dashboard_api/connectors/toss/client.py`
  - `services/api/src/toss_dashboard_api/connectors/toss/rate_limit.py`
  - `services/api/src/toss_dashboard_api/connectors/toss/errors.py`
  - `services/api/src/toss_dashboard_api/connectors/toss/models.py`
  - connector unit tests와 opt-in `scripts/toss-live-preflight.ps1`
- 수정 가능한 기존 파일: `config.py`, `logging_config.py`, `pyproject.toml`, `requirements.in`, `requirements.lock`, `scripts/policy-scan.ps1`, `scripts/secret-scan.ps1`, `test_no_external_network.py`
- DB migration: 없음; token·credential 저장 금지
- fixture: token fixture 파일 금지. 시장 API용 비식별 error/rate response fixture만 허용
- unit test: token expiry, single-flight, 이전 token 폐기, header parsing, group isolation, retry budget, error taxonomy
- integration test: `httpx.MockTransport`로 auth→GET, 401 refresh 1회, 429, 5xx, schema error
- live test: explicit opt-in preflight에서 token 발급과 안전한 `GET /api/v1/stocks` 1건만; stdout/body/token 저장 금지
- offline regression: 표준 `scripts/test.ps1`은 socket 차단 상태로 전부 PASS
- security test: exact host/path/method, redirect/TLS, redaction, 금지 endpoint와 account header canary
- rollback: connector/config/dependency/policy 변경 revert; 저장 데이터 없음
- 완료 조건: credential 없이 offline 전 검증 PASS, credential preflight는 미실행이어도 `[LIVE_UNVERIFIED]`로 명시 가능

### CP3-A — Security Master + Current Price 계획·계약

- 변경 범위: `plans/PHASE_02_CP3_A_CONTRACT.md`와 승인된 상태/ADR/known-issue 문서만
- application/test/fixture/migration/dependency/runtime config/API route/connector 변경: 0
- actual credential/API usage: 0
- 계약 범위: endpoint 역할, universe, provider staging identity, lifecycle, ProviderPriceSnapshot/canonical current-price view, nullable source time, raw/source/hash/idempotency, additive migration과 acceptance
- 독립검증 보완: P1-01 provider price를 nullable canonical linkage와 분리; P1-02 continuity-first reconciliation과 enrichment/no-rekey/collision algorithm 및 P0 acceptance 추가
- 상태: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
- 완료 표현 금지: 독립 검토·사용자 승인 전 `PASS`, `APPROVED`, `COMPLETE` 금지
- rollback: documentation commit revert; application/data 영향 없음

### CP3-B — Contract Foundation + Additive Migration + Raw/Source Trace

- provider-specific versioned contract와 source timestamp/date/missing semantics
- exact enum contract, additive `0002_phase_02_cp3_foundation` migration, raw manifest/source metadata, repository interface
- offline fixture/test only; application collection job와 live API 없음
- Phase 1 SourceRecord/Issuer/Security v0.1.0, fixture/API/OpenAPI와 `0001` 변경 금지
- 시작 조건: CP3-A GPT 재검토와 사용자 승인, ADR-011/ADR-012 disposition 확정

### CP3-C — Security Master

- `/stocks/all` discovery DTO/fixture와 `/stocks` detail DTO/fixture
- KR/US conservative universe, provider staging identity, canonical mapping, lifecycle, normalization, storage와 idempotency
- unknown enum, identifier collision, symbol reuse와 partial detail negative test
- live API 없음
- 시작 조건: CP3-B 승인 및 full offline gate 통과

### CP3-D1 — Current Price Offline

- `/prices` DTO/fixture, 최대 200-symbol chunking, strict Decimal/currency/timestamp-null 계약
- valid provider identity 기준 ProviderPriceSnapshot, nullable canonical linkage와 verified-only canonical view
- raw/source trace, provider latest-state, duplicate/revision, last known-good 보존
- price history SQLite 누적 금지; CP4 Parquet/DuckDB 범위 유지
- full offline regression
- 시작 조건: CP3-C 승인

### CP3-D2 — Separately Approved Minimal Live Verification

- 사용자 별도 승인 전 실행 금지
- 승인된 소수 symbol만 `/stocks/all`과 `/prices` schema/header/timestamp semantics 최소 대조
- 값, body, token, raw header와 credential 저장 금지
- account/order/WebSocket 금지, exact callable allowlist 확대 금지
- 시작 조건: CP3-D1 승인과 별도 live 승인

### CP3-D3 — Integrated QA and Closeout

- 전체 회귀, migration/idempotency/OpenAPI/build/E2E/secret/policy/false-green gate
- P0/P1/P2 분류와 문서 closeout
- CP3 완료 여부는 D3 독립 검토와 사용자 승인 뒤에만 판정

각 CP3 checkpoint는 앞 checkpoint 승인 뒤에만 시작한다. CP3-A 뒤 CP3-B/C/D를 자동 실행하지 않는다. 세부 계약과 test-case matrix는 `plans/PHASE_02_CP3_A_CONTRACT.md`를 따른다.

### CP4 — Candles + time-series storage

- 구현 파일: candle normalizer/job, Parquet writer, DuckDB read adapter, manifest/atomic publish
- 수정 가능한 기존 파일: `PriceBar` interval·adjustment 계약, analytics repository, dependency locks, build/test scripts
- DB migration: analytics manifest·job pointer metadata가 필요할 때만 한 개의 forward migration
- fixture: KR/US 1m·1d, adjusted true/false, empty/last page, invalid OHLC, duplicate page boundary
- unit test: OHLC invariant, nonnegative volume, UTC/KST/US offset, date, nextBefore inclusive paging, Decimal exactness
- integration test: multi-page fetch, retry 후 중복 없음, atomic failure recovery, DuckDB query roundtrip
- live test: 소수 symbol·짧은 page에서 ordering, page boundary, adjusted semantics `[LIVE_UNVERIFIED]` 해소
- offline regression: network 0, existing build/E2E 포함 전체 PASS
- security test: raw path traversal·symlink/reparse 방지, credential absence, safe temp cleanup
- rollback: 새 manifest publish 중지, 이전 manifest pointer 복원; raw/history 자동 삭제 금지
- 완료 조건: 1m·1d durable query, 멱등성, crash-safe publish, source 추적 PASS

### CP5 — Investor / Program / Short / Credit / Lending flows

- 구현 파일: 5 endpoint DTO·normalizer·job, dataset별 Parquet schema와 query adapter
- 수정 가능한 기존 파일: market contracts/enums, data-quality mapping, analytics repository
- DB migration: source/job metadata에 dataset 상태가 부족할 때만 forward migration; 수급 시계열은 SQLite 금지
- fixture: 당일 잠정, 저녁 반영, T+1, nullable breakdown/rate/object, negative net buy, empty page, correction
- unit test: KR-only, integer-valued Decimal, 음수 순매수, 암묵적 KRW, null reason, date-only, nested sum invariant
- integration test: until/nextUntil pagination, 5 dataset 장애 격리, same-key hash revision, 재수집 멱등성
- live test: 공식 timing window별 최소 sample을 별도 승인 일정으로 관찰; exact 값은 evidence에 저장하지 않음
- offline regression: Phase 1 fixture와 CP2~4 offline suite 전부 PASS
- security test: symbol/path validation, account/order header 부재, source body log 금지
- rollback: dataset별 publish pointer를 이전 version으로 복구; raw append 보존
- 완료 조건: 5 dataset 모두 availability/freshness/finality/revision을 거짓 없이 표현, P0/P1 0

### CP6 — Freshness / Data Quality / 통합 QA

- 구현 파일: source별 scheduler/job runner, freshness policy, Data Quality publish, Phase 2 QA artifacts
- 수정 가능한 기존 파일: system/data-quality API, 기존 Data Quality UI의 source 상태 표시, scripts/test, STATUS/CHANGELOG/KNOWN_ISSUES
- DB migration: scheduler/audit 상태에 꼭 필요한 항목만; backup·restore 영향 문서화
- fixture: auth/rate/partial failure/stale/expired/unknown enum/schema drift 시나리오
- unit test: calendar 기반 scheduling, freshness 경계, partial/degraded/error state, retry reschedule
- integration test: fetch→raw→validate→normalize→upsert→publish 전체 경로와 source 장애 격리
- live test: credential preflight + 승인된 작은 sample의 schema/header/freshness 대조
- offline regression: lint, typecheck, backend/frontend, migration, idempotency, OpenAPI drift, build, E2E, secret/policy 전부 PASS
- security test: browser bundle·Git·로그·QA artifact secret scan, forbidden route/header/dependency canary
- rollback: scheduler 중지 → last known-good manifest/read adapter → connector disable; 검증된 과거 데이터 삭제 금지
- 완료 조건: Phase 2 전체 gate, self QA, 독립 리뷰 준비 자료, 문서 갱신 완료

## 14. checkpoint별 acceptance criteria

| checkpoint | 필수 acceptance |
|---|---|
| CP1 | 공식 source hash·version, 17개 endpoint 조사, 12개 callable allowlist, 9개 rate group, 미확인·문서 충돌 기록, application diff 0 |
| CP2 | single backend token manager, single-flight, memory-only, exact host/path, bounded retry, offline PASS, 계좌·주문 fail-closed |
| CP3-A | Security Master/Current Price 계획·계약, ADR-011 proposed/ADR-012 revised proposed, P1-01/P1-02 보완, application diff 0, GPT 재검토 대기 |
| CP3-B | versioned provider contract, additive migration, raw/source trace와 offline acceptance |
| CP3-C | KR/US master strict normalize, staging/canonical stable mapping, lifecycle/collision/idempotency |
| CP3-D1 | provider-scoped current price offline Decimal/time/null/currency/source/latest/idempotency/revision와 verified-only canonical view |
| CP3-D2 | 별도 승인된 최소 live schema/header/timestamp 대조; secret/body/raw header persistence 0 |
| CP3-D3 | full regression, migration, idempotency, build/E2E/secret/policy/false-green와 P0/P1 0 |
| CP4 | 1m·1d candles, durable Parquet/DuckDB, atomic publish, paging·adjustment·timezone·OHLC 검증 |
| CP5 | 5개 KR flow dataset, 잠정/UNKNOWN의 정직한 표현, revision/history, 장애 격리·멱등성 |
| CP6 | rate/freshness/data-quality end-to-end, full offline regression, approved live comparison, P0=0·P1=0 |

checkpoint 완료를 다음 checkpoint 완료로 대신하지 않는다. live 검증이 필수 acceptance로 승격되면 credential·허용 IP 없이는 `PARTIAL`로 보고한다.

## 15. 테스트 전략

1. strict contract: extra forbid, Decimal string, aware UTC, date-only, missing reason, unknown enum
2. connector unit: request construction, allowed host/path/method, form auth, response schema, no account header
3. rate/retry: group isolation, all rate headers, Retry-After, bounded attempts, reschedule
4. raw: hash, append-only, atomicity, reparse/path traversal, no auth material
5. normalization: source trace, stable key, unit/currency, null/finality/revision
6. storage: migration, Parquet schema, DuckDB roundtrip, idempotency, rollback pointer
7. integration: success, partial, schema drift, auth failure, 429, 5xx, source isolation
8. offline: pytest socket 차단 아래 모든 fixture 테스트
9. frontend: Toss 직접 호출·secret 번들 부재와 기존 UI 회귀
10. security: secret scan + deny-by-default policy canary

테스트 삭제·skip·xfail·조건부 우회로 기존 inventory를 줄이지 않는다.

## 16. live vs offline 검증 분리

### Offline — 기본·필수

- `scripts/setup.ps1`, `scripts/test.ps1`은 credential 없이 통과
- 외부 socket 차단
- 공식 schema 기반 비식별 fixture와 MockTransport
- token 문자열은 파일 fixture가 아니라 테스트 프로세스 메모리의 분할 canary만 사용
- CI/일반 QA는 live endpoint를 호출하지 않음

### Live — 명시적 opt-in

- 별도 `scripts/toss-live-preflight.ps1 -Live` 형태
- `TOSS_LIVE_ENABLED=true` 같은 명시적 gate와 필수 안전 플래그 확인
- env 또는 gitignored `.env`만 읽고 prompt 입력 금지
- token/client 값, Authorization, 전체 body를 stdout·파일·QA evidence에 출력하지 않음
- 확인 결과는 status, schema field presence, latency, rate 숫자, request ID 존재 여부만 redacted summary로 남김
- account/order endpoint와 header는 live에서도 절대 사용하지 않음

## 17. secret handling

- `client_id`, `client_secret`, `access_token`은 DB, Git, raw, fixture, log, traceback, browser, QA evidence에 저장하지 않음
- `.env.example`에는 변수명과 빈 값만 허용
- `.env`는 gitignore 유지, 파일 권한·reparse 여부를 preflight에서 검사
- 환경변수 누락은 안전한 실패이며 interactive secret prompt로 우회하지 않음
- `logging_config.py`의 key/value redaction에 Toss credential naming을 포함
- HTTP event log는 method, allowlisted path template, status, latency, rate 숫자만 허용
- query에 credential 금지
- process command line argument로 secret 전달 금지
- crash dump·exception repr에 request headers/body가 들어가지 않게 custom exception을 사용

## 18. rollback

공통 rollback 순서:

1. scheduler와 live connector를 비활성화한다.
2. fixture-only repository 또는 last known-good analytics manifest로 전환한다.
3. 새 normalized publish를 중지하되 raw·검증된 과거 데이터를 삭제하지 않는다.
4. 코드·dependency·policy 변경은 checkpoint 단위 commit revert로 복구한다.
5. DB downgrade가 필요하면 backup 후 disposable copy에서 먼저 검증하고 명시적 승인 없이 실제 DB에 destructive downgrade하지 않는다.
6. token은 메모리에서 폐기하며 revoke endpoint를 추측하거나 호출하지 않는다.

## 19. KNOWN_ISSUES

### KI-P2-01 — live contract 부분 검증

- `[LIVE_VERIFIED]` actual OAuth token issuance, credential acceptance, allowed-IP 실행 경로, `GET /api/v1/stocks`, 성공 Limit/Remaining/Reset header
- `[LIVE_UNVERIFIED]` natural 429 `Retry-After`, actual 429/5xx, production retry timing, `/stocks/all`, `/prices`, 나머지 market endpoint와 CP3 data semantics/freshness
- 해결: endpoint별 승인 checkpoint에서 최소 범위를 별도 검증하며 미검증 항목을 소급 승격하지 않음

### KI-P2-02 — 공식 WebSocket 문서 상태 충돌

- indexed interactive Market Data 문서는 “웹 소켓은 추후 지원 예정” 문구를 노출한다.
- canonical `llms.txt`, overview와 AsyncAPI v1.2.2는 WebSocket server·channel을 완전히 정의한다.
- source 우선순위상 canonical AsyncAPI를 현재 계약으로 인정한다.
- Phase 2 결정은 기능 부재가 아니라 범위 제한에 의한 REST-only다.
- 재검토: 별도 WebSocket checkpoint와 사용자 승인, order-event 채널 제외 정책이 준비될 때

### KI-P2-03 — 명시적 finality flag 부재

- 공식 문서는 일부 반영 시점을 설명하지만 scoped response에 공통 finality boolean/enum은 없다.
- 해결 전 기본 `UNKNOWN`, 명백한 장중 변경 가능 값만 `PRELIMINARY`.

### KI-P2-04 — SourceRecord date-only·publication semantics

- Phase 1 SourceRecord의 필수 datetime이 date-only 수급, publication 미제공과 `/prices timestamp=null`을 정확히 표현하지 못한다.
- 해결: 기존 v0.1.0을 완화하지 않고 observed time/date 둘 다 null + structured reason을 허용하는 versioned provider source contract를 ADR-011 revised proposal로 독립 검토한 뒤 CP3-B에서 구현.

### KI-P2-05 — schema·rate drift

- `latest` URL과 rate 수치는 변경 가능하다.
- 해결: CP 시작 시 version/hash 재확인, runtime header 하향 우선, schema drift fail closed.

### KI-P2-06 — Toss issuer identity conflict

- Toss stock detail에는 Phase 1 `Issuer`가 요구하는 KR corp_code/US CIK가 없고 exchange semantics도 현재 미확인이다.
- 해결: Toss symbol/ticker를 regulatory ID로 위조하지 않고 ADR-012의 provider staging identity를 사용한다. valid identity의 provider-scoped price storage는 canonical mapping 없이 허용하되 canonical Issuer/Security 자동 생성, canonical price view와 issuer/company analysis 연결은 verified mapping 전 금지한다. allocation은 기존 continuity를 먼저 찾고 identifier enrichment로 rekey하지 않는다.

### KI-P2-07 — source revision/natural key conflict

- 기존 `source_records(source_system, source_type, external_id)` unique는 반복 price snapshot과 same-key revision을 표현하지 못한다.
- 해결: timestamp suffix로 회피하지 않고 additive provider source-version table, semantic normalized hash와 latest pointer를 CP3-B proposal로 검토한다.

## 20. Phase 2 완료 게이트

Phase 2 완료 선언에는 모두 필요하다.

- P0 = 0
- P1 = 0
- P2 = 수정 또는 사용자 승인 이월
- callable allowlist 밖의 Toss endpoint runtime code = 0
- account/order/conditional-order code·header·config = 0
- WebSocket/OpenAI/OpenDART/SEC/news/macro code = 0
- token single-flight·memory-only·redaction PASS
- documented/observed/effective rate 분리와 bounded retry PASS
- 종목 mapping, Decimal, date/time, null, finality, revision 계약 PASS
- raw→normalized→analytics source trace와 멱등성 PASS
- source별 장애 격리와 last known-good 보존 PASS
- standard offline full suite, migration, fixture idempotency, build, E2E PASS
- secret scan과 Phase 2 policy scan PASS
- 승인된 최소 live schema/rate/freshness 대조 또는 명시적 미검증 승인
- `qa/PHASE_02_SELF_QA.md`, `STATUS.md`, `CHANGELOG.md`, `KNOWN_ISSUES.md` 갱신
- 별도 독립 리뷰 준비 완료

## 최종 판정

CP1은 `PASS`, CP2는 `COMPLETE`다. CP3-A는 독립검증 P1-01/P1-02에 맞춰 계획·계약을 보완했으며 상태는 `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`다. `PASS`, `APPROVED`, `COMPLETE`가 아니다. ADR-010은 `ACCEPTED`, ADR-011 proposal과 revised ADR-012 proposal은 승인되지 않았다. CP3-B는 `NOT STARTED`이고 재검토와 사용자 승인 전 자동 진행은 `PROHIBITED`다. Phase 2 전체는 `IMPLEMENTATION IN PROGRESS`다.
