# Phase 2 CP3-A — Security Master + Current Price 계획·계약

- 문서 상태: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- 작성일: `2026-08-24` (`Asia/Seoul`)
- 기준 브랜치: `feature/phase-02-toss`
- 시작 commit: `6bd5d2ae9c26f02f2cd4bd75a474633a9082fa16`
- checkpoint 경계: `CP3-A documentation/contract only`
- 후속 상태: `CP3-B NOT STARTED`

이 문서는 CP3-B 이후 구현에 앞선 승인안이다. 문서가 작성됐다는 사실은 계약의 `PASS`, ADR의 `ACCEPTED`, application 구현 승인, live endpoint 검증 또는 Phase 2 완료를 뜻하지 않는다.

## 근거 표기

| 표기 | 의미 |
|---|---|
| `[CURRENT_REPO_FACT]` | 현재 commit의 문서, 계약, ORM, migration 또는 connector code에서 직접 확인한 사실 |
| `[OFFICIAL_DOC_CONTRACT]` | 저장소의 2026-08-23 canonical Toss OpenAPI 조사 기록에 근거한 공개 provider 계약 |
| `[LIVE_VERIFIED]` | 2026-08-24 CP2-D2의 redacted one-shot 결과로 실제 확인한 최소 범위 |
| `[LIVE_UNVERIFIED]` | 공식 계약 또는 계획은 있으나 해당 endpoint/field/semantics를 실제 응답으로 확인하지 않은 범위 |
| `[PROPOSED_REPO_CONTRACT]` | 이 문서가 독립 검토와 사용자 승인을 요청하는 신규 저장소 계약 |
| `[USER_DECISION_REQUIRED]` | 구현 전에 독립 검토와 사용자의 명시적 결정이 필요한 항목 |

각 결정은 위 근거를 명시한다. 서로 다른 근거가 한 행에 있으면 확인된 사실과 제안 범위를 문장으로 분리한다.

## A. 목적과 범위

- `[CURRENT_REPO_FACT]` Phase 1 `SourceRecord`, `Issuer`, `Security`, `PriceBar` v0.1.0과 SQLite `0001_phase_01`이 존재한다.
- `[CURRENT_REPO_FACT]` CP2는 exact REST allowlist, memory-only OAuth token, bounded retry, offline/live 경계를 구현했고 `COMPLETE`다.
- `[LIVE_VERIFIED]` canonical provider contract drift 없음, OpenAPI `3.1.0`, provider REST `1.2.14`, actual OAuth issuance, credential acceptance, allowed-IP 실행 경로, `GET /api/v1/stocks`, 성공 응답의 Limit/Remaining/Reset rate header만 확인됐다.
- `[LIVE_UNVERIFIED]` `/api/v1/stocks/all`, `/api/v1/prices`, 전체 market/enum/null/freshness semantics, natural 429와 actual 429/5xx는 확인되지 않았다.
- `[PROPOSED_REPO_CONTRACT]` CP3-A는 Security Master와 Current Price의 endpoint 역할, identity, lifecycle, source trace, idempotency, additive migration, offline acceptance를 계약화한다. application, test, fixture, migration, dependency, runtime config, route 또는 collection job은 만들지 않는다.

## B. Phase 1 계약과의 호환성

### B.1 보존할 계약

- `[CURRENT_REPO_FACT]` 전역 `ContractVersion`은 `Literal["0.1.0"]`이고 `StrictContract`는 `extra="forbid"`, canonical Decimal string, aware UTC를 강제한다.
- `[CURRENT_REPO_FACT]` `Issuer`는 KR `corp_code`, US `cik`를 강제한다. 오류 문구가 synthetic identifier를 언급하지만 이는 Phase 1 합성 fixture 조건이며 실제 Toss symbol을 그 필드에 넣을 근거가 아니다.
- `[CURRENT_REPO_FACT]` `Security`는 `issuer_id`, `exchange`, `ticker`, `share_class`, `currency`를 요구하고 `mapping_status`는 `VERIFIED|UNRESOLVED`다.
- `[CURRENT_REPO_FACT]` `SourceRecord` v0.1.0은 `observed_at`, `published_at`, `fetched_at`을 모두 required aware datetime으로 요구한다.
- `[CURRENT_REPO_FACT]` `source_records`에는 `(source_system, source_type, external_id)` unique 제약이 있어 같은 자연키의 반복 가격 payload와 revision을 한 행 집합으로 표현할 수 없다.
- `[PROPOSED_REPO_CONTRACT]` 위 계약, Phase 1 fixture/API/OpenAPI, `0001_phase_01`과 기존 row는 수정·완화·backfill하지 않는다. 신규 provider staging/source 계약은 별도 version과 additive table을 사용한다.

### B.2 현재 문서·코드 충돌과 disposition

| 충돌 | 영향 | disposition |
|---|---|---|
| `[CURRENT_REPO_FACT]` `docs/04` SecurityMaster 예시는 `corp_code=null`, `cik=null`, `mapping_status=VERIFIED`지만 실제 `Issuer` validator는 jurisdiction별 regulatory ID를 강제 | Toss만으로 canonical issuer를 만들면 거짓 ID 또는 validation 실패 | `[PROPOSED_REPO_CONTRACT]` provider staging identity에서 `mapping_status=UNRESOLVED`, explicit missing reason을 사용하고 canonical row publish 금지 |
| `[CURRENT_REPO_FACT]` `Security.exchange` required이나 현재 CP3 근거에는 Toss exchange semantics가 확정돼 있지 않음 | 임의 exchange 생성 위험 | `[PROPOSED_REPO_CONTRACT]` exchange가 검증될 때까지 staging 유지 |
| `[CURRENT_REPO_FACT]` `SourceRecord` 관측/발표 시각 required, `[OFFICIAL_DOC_CONTRACT]` price timestamp nullable | fetch 시각을 관측시각으로 위조할 위험 | `[PROPOSED_REPO_CONTRACT]` ADR-011 revised provider source contract 사용 |
| `[CURRENT_REPO_FACT]` Phase 1 source unique key는 revision 불가 | timestamp suffix로 멱등성을 회피할 위험 | `[PROPOSED_REPO_CONTRACT]` 신규 provider source-version table과 latest pointer로 분리 |

## C. Toss endpoint 역할

### C.1 `GET /api/v1/stocks/all`

- `[OFFICIAL_DOC_CONTRACT]` `market`을 받아 KR/US universe 목록을 반환하는 discovery endpoint다.
- `[LIVE_UNVERIFIED]` 실제 KR/US body, 목록 완전성, enum/null semantics는 확인하지 않았다.
- `[PROPOSED_REPO_CONTRACT]` KR과 US를 별도 canonical request로 조회한다. 최초 범위는 `ACTIVE`, common share, 명시적으로 지원된 stock type 후보뿐이다.
- `[PROPOSED_REPO_CONTRACT]` discovery 후보 생성 전용이다. 상세 Security Master의 단독 최종 source로 사용하지 않는다.
- `[PROPOSED_REPO_CONTRACT]` 이전 목록에서 사라진 것은 `DISCOVERY_MISSING` observation일 뿐 `INACTIVE` 또는 `DELISTED`가 아니다.

### C.2 `GET /api/v1/stocks`

- `[OFFICIAL_DOC_CONTRACT]` `symbols` 1~200개를 쉼표로 전달하고 `symbol`, `name`, `englishName`, `isinCode`, `market`, `securityType`, `isCommonShare`, `status`, `currency`, `listDate`, `delistDate`, `sharesOutstanding`, `leverageFactor`, `koreanMarketDetail`을 제공하는 detail 후보 endpoint다.
- `[LIVE_VERIFIED]` actual OAuth 뒤 이 endpoint를 호출하는 구조와 성공 response outer structure만 확인됐다.
- `[LIVE_UNVERIFIED]` 전체 market, enum, nullable field, ISIN, status/list/delist semantics는 검증되지 않았다.
- `[PROPOSED_REPO_CONTRACT]` discovery 후보를 최대 200 symbols씩 detail-enrich한다. response에 누락된 후보는 `PARTIAL_DETAIL`로 격리하고 빈 값으로 채우지 않는다.

### C.3 `GET /api/v1/prices`

- `[OFFICIAL_DOC_CONTRACT]` `symbols` 1~200개와 `symbol`, nullable `timestamp`, Decimal string `lastPrice`, `currency`를 사용한다.
- `[LIVE_UNVERIFIED]` endpoint body, timestamp-null 빈도와 의미, 가격/currency semantics는 실제 확인하지 않았다.
- `[PROPOSED_REPO_CONTRACT]` canonical `security_id`로 성공적으로 mapping되고 lifecycle/currency가 eligible인 security만 요청한다.
- `[PROPOSED_REPO_CONTRACT]` unresolved, quarantined, collision 또는 stale-mapping security에는 normalized current price와 latest pointer를 publish하지 않는다.

fallback endpoint, symbol 변환 규칙, exchange inference 또는 추가 endpoint는 추측하지 않는다. 기존 exact callable allowlist도 확대하지 않는다.

## D. KR/US universe

### D.1 보수적 초기 범위

| provider field | exact accepted input | internal result | 다른 값 |
|---|---|---|---|
| `market` | `KR` | `Market.KR` | unknown은 raw 보존 + record quarantine |
| `market` | `US` | `Market.US` | unknown은 raw 보존 + record quarantine |
| `status` | `ACTIVE` | discovery eligible candidate | `INACTIVE`/`DELISTED`는 비eligible lifecycle observation, unknown은 quarantine |
| `isCommonShare` | JSON boolean `true` | common-share candidate | `false`는 제외; 문자열/숫자/default coercion 금지 |
| `securityType` | canonical provider schema에서 common stock으로 명시된 exact token | `ShareClass.COMMON` 후보 | ETF/ETN/preferred/warrant/fund/bond/unknown과 미확인 token은 제외 또는 quarantine |
| `currency` | KR + `KRW` | `Currency.KRW` 후보 | mismatch/unknown은 `DEGRADED`, publish 금지 |
| `currency` | US + `USD` | `Currency.USD` 후보 | mismatch/unknown은 `DEGRADED`, publish 금지 |

- `[CURRENT_REPO_FACT]` 현재 저장소에는 exact provider `securityType` enum value set이 snapshot으로 보존돼 있지 않다.
- `[OFFICIAL_DOC_CONTRACT]` `status=ACTIVE`, `securityType`, common-share filter와 KR/US market이 문서화돼 있다.
- `[LIVE_UNVERIFIED]` 전체 enum set과 실제 market별 값은 미검증이다.
- `[PROPOSED_REPO_CONTRACT]` CP3-B는 저장된 canonical contract evidence로 common-stock exact token을 먼저 고정해야 하며, 확인 전에는 symbolic 추정값을 runtime allowlist로 만들 수 없다. 확인되지 않은 값은 항상 fail closed한다.
- `[USER_DECISION_REQUIRED]` exact provider enum table은 독립 검토에서 canonical evidence와 대조 후 승인해야 한다. 이 문서가 enum spelling을 새 provider 사실로 발명하지 않는다.

### D.2 universe publish 조건

아래 조건을 모두 만족할 때만 staging candidate를 `ELIGIBLE_FOR_MAPPING`으로 표시한다.

1. market exact mapping 성공
2. status exact `ACTIVE`
3. supported common-stock security type exact match
4. `isCommonShare is true`
5. non-empty provider symbol/name
6. detail response와 discovery identity가 충돌하지 않음
7. currency가 market expectation과 일치
8. identifier collision 없음

`ELIGIBLE_FOR_MAPPING`은 canonical mapping `VERIFIED`와 다르며 price publish 권한을 주지 않는다.

## E. issuer/security/provider identifier

### E.1 금지 규칙

- Toss symbol/ticker를 `corp_code` 또는 `CIK`로 저장하지 않는다.
- synthetic regulatory identifier를 생성하지 않는다.
- 종목명 또는 영문명 일치만으로 issuer를 병합하지 않는다.
- ISIN 하나만으로 issuer와 security를 동일 object로 취급하지 않는다.
- unknown/collision mapping을 `VERIFIED`로 저장하지 않는다.
- provider field 변경을 이유로 이미 발급된 internal ID를 교체하지 않는다.

### E.2 대안 비교

| 대안 | 장점 | 결함 | 권고 |
|---|---|---|---|
| provider-scoped provisional issuer | 기존 canonical shape와 비슷함 | 실제 발행사 근거 없이 가짜 issuer가 늘고 이름 merge 유혹이 큼 | 거부 |
| canonical Security 이전 provider staging identity | regulatory ID 부재를 정직하게 보존하고 mapping을 지연 | 신규 staging schema와 promotion 절차 필요 | **권고** |
| 기존 Issuer 계약 breaking 완화 | 단기 구현은 단순 | Phase 1 fixture/API/OpenAPI 회귀와 거짓 VERIFIED row 위험 | 기본 거부 |

- `[PROPOSED_REPO_CONTRACT]` ADR-012에 따라 `provider_security_identity`와 canonical `Issuer`/`Security`를 분리한다.
- `[PROPOSED_REPO_CONTRACT]` staging row는 nullable `issuer_id`/`security_id`, `mapping_status=UNRESOLVED`, `missing_reasons.issuer_id=UNRESOLVED`, 필요 시 `missing_reasons.security_id=UNRESOLVED`를 가진다.
- `[PROPOSED_REPO_CONTRACT]` OpenDART corp_code 또는 SEC CIK와 instrument mapping이 승인될 때만 canonical mapping event를 만들 수 있다.

### E.3 exact ID/allocation algorithm

문자열은 UTF-8, separator `|`, Unicode NFC, provider symbol의 case는 원문을 보존하되 provider가 명시한 canonical case만 사용한다. 임의 upper/lower 변환은 하지 않는다.

1. `canonical_request_id = "treq_" + sha256(method|path_template|canonical_query)`의 64 lowercase hex.
2. 최초 staging anchor 우선순위:
   - unique·valid ISIN이 있으면 `toss-identity-v1|market|ISIN|isin`;
   - 아니면 non-null list date가 있으면 `toss-identity-v1|market|SYMBOL_LIST_DATE|symbol|listDate`;
   - 둘 다 없으면 raw history에서 정렬상 최초 valid observation의 `toss-identity-v1|market|FIRST_SEEN_RAW|symbol|raw_content_hash`.
3. `provider_security_identity_id = "tpsi_" + SHA-256(anchor)` 전체 64 lowercase hex.
4. 같은 anchor는 항상 같은 ID를 반환한다. full digest ID가 다른 anchor와 충돌하면 suffix나 현재 시각을 붙이지 않고 collection을 `BLOCKED_COLLISION`으로 중단한다.
5. allocation registry는 anchor, full digest, first source version과 mapping history를 보존한다. deterministic rebuild는 append-only raw/source manifest를 `(fetched_at, source_version_id)`로 정렬하고 동일 우선순위를 적용한다. 최초 승인 mapping event가 있으면 그 event가 anchor 선택보다 우선한다.
6. 기존 Phase 1 `issuer_id`/`security_id`는 grandfathered ID로 그대로 둔다.
7. 신규 canonical issuer는 승인된 regulatory anchor만 허용한다: `issuer-v1|KR|CORP_CODE|corp_code` 또는 `issuer-v1|US|CIK|cik`; `issuer_id = "issuer_" + SHA-256(anchor)`.
8. 신규 canonical security는 승인된 mapping event의 immutable anchor `security-v1|issuer_id|instrument_identifier_kind|instrument_identifier`로 `security_id = "sec_" + SHA-256(anchor)`를 만든다. ISIN이 후일 변경돼도 ID를 재발급하지 않고 identifier history/revision을 추가한다.
9. canonical anchor collision, duplicate active ISIN 또는 서로 다른 issuer 후보는 자동 병합하지 않고 `UNRESOLVED_COLLISION`으로 격리한다.

- `[PROPOSED_REPO_CONTRACT]` 위 알고리즘은 CP3-B 구현 제안이며 독립 검토 전 확정이 아니다.
- `[USER_DECISION_REQUIRED]` 신규 canonical ID algorithm과 promotion authority를 승인해야 CP3-C mapping 구현을 시작할 수 있다.

### E.4 identifier history cases

| case | required behavior |
|---|---|
| symbol 변경 + 같은 verified ISIN | 기존 provider identity/internal ID 유지, old symbol `valid_to`, new symbol `valid_from`, mapping review event |
| 같은 symbol + ISIN 변경 | 자동 overwrite 금지; share/class/corporate-action evidence 전까지 신규 candidate 또는 collision quarantine |
| symbol 재사용 | old lifecycle close 후 별도 staging identity; old ID 부활 금지 |
| ISIN missing | explicit `NOT_PROVIDED`; name-only promotion 금지 |
| ISIN change | old value history 보존, source revision과 mapping review 필수 |
| ISIN collision | 모든 관련 candidate quarantine; 하나를 임의 winner로 선택 금지 |
| market change | 동일 symbol이어도 별도 provider identifier validity; canonical merge는 승인 evidence 필요 |
| share-class change | in-place class overwrite 금지; 새 security 후보로 처리 |
| delisting/relisting | old validity close와 new observation 분리; 같은 ID 재사용은 verified continuity evidence가 있을 때만 |

## F. lifecycle/status/listing/delisting

### F.1 state observations

`DISCOVERED`, `DETAIL_VALID`, `ELIGIBLE_FOR_MAPPING`, `MAPPED_VERIFIED`, `DISCOVERY_MISSING`, `INACTIVE_OBSERVED`, `DELISTED_OBSERVED`, `QUARANTINED`는 provider staging workflow 상태다. Phase 1 public enum을 변경하지 않는다.

| condition | proposed handling |
|---|---|
| ACTIVE → INACTIVE/DELISTED detail | new source version과 lifecycle event; latest eligible=false; 이전 verified row/history 보존 |
| `/stocks/all` 일시 누락 | `DISCOVERY_MISSING`; canonical delisting/valid_to 생성 금지; detail 재확인 전 LKG 보존 |
| `listDate=null` | `missing_reason=NOT_PROVIDED`; 임의 date 금지; 다른 조건이 유효해도 mapping review 필요 |
| `delistDate=null` + ACTIVE | 정상 nullable 후보, `NOT_APPLICABLE` 또는 provider-specific reason; delisting 추론 금지 |
| `delistDate=null` + DELISTED | missing reason 필수, lifecycle date 미확정; quarantine/review |
| ACTIVE + non-null past delistDate | contradiction; raw 보존, 신규 publish 금지, LKG 유지 |
| status와 future delistDate | 예정 상태 의미를 추측하지 않고 quarantine/review |
| exchange 미확인 | staging 유지; required canonical `Security.exchange` 위조 금지 |
| common flag/type 불일치 | contradiction quarantine; 한 필드로 다른 필드를 덮어쓰기 금지 |
| 신규 snapshot schema 오류 | raw/source version 보존; normalized publish 금지; LKG 유지 |

- `[PROPOSED_REPO_CONTRACT]` lifecycle은 observation history이며 단일 discovery snapshot의 부재를 사실로 승격하지 않는다.
- `[LIVE_UNVERIFIED]` provider status/delist transition semantics는 CP3-D2 전까지 live verified가 아니다.

## G. Current Price 계약

### G.1 `PriceSnapshot` field contract

| field | type/rule |
|---|---|
| `price_snapshot_id` | deterministic `SafeId`; semantic key + normalized hash로 생성 |
| `security_id` | verified canonical security ID; unresolved이면 normalized publish 금지 |
| `provider_symbol` | source spelling을 보존한 provider-scoped identifier |
| `last_price` | canonical non-exponent Decimal JSON string; binary float/JSON number 금지 |
| `currency` | provider response exact value를 보존하고 internal exact enum과 별도 검증 |
| `provider_timestamp` | nullable aware provider timestamp; normalized value는 UTC |
| `fetched_at` | required aware UTC response-complete time |
| `source_record_id` | 신규 provider source-version record ID |
| `raw_content_hash` | exact response raw bytes SHA-256 |
| `normalized_content_hash` | 아래 semantic field set의 canonical SHA-256 |
| `contract_version` | provider price contract 전용 version; 전역 v0.1.0 Literal과 분리 |
| `freshness_status` | `FRESH|STALE|EXPIRED|UNKNOWN`; timestamp null이면 반드시 `UNKNOWN` |
| `availability_status` | `AVAILABLE|DEGRADED|ERROR|UNAVAILABLE` |
| `revision_status` | `ORIGINAL|AMENDED|SUPERSEDED`; duplicate는 신규 revision이 아님 |

### G.2 Decimal rules

- 허용 grammar: `0` 또는 `[1-9][0-9]*(\.[0-9]+)?`; leading plus, leading zero, exponent, NaN, Infinity, whitespace, JSON number와 binary float를 거부한다.
- `last_price > 0`일 때만 active common security의 current/latest publish 후보가 된다.
- exact string `0`은 missing으로 바꾸지 않지만 `NON_POSITIVE_PRICE` quality flag와 `DEGRADED` quarantine으로 처리해 latest pointer를 갱신하지 않는다.
- 음수와 `-0`은 contract error로 reject한다.
- 규모 상한을 binary float로 두지 않는다. storage length/Decimal precision 한계는 CP3-D1 test에서 explicit arbitrary-precision boundary로 정한다.

### G.3 timestamp/null/freshness/availability

| input state | availability | freshness | normalized/latest behavior |
|---|---|---|---|
| mapped, positive price, currency match, aware timestamp | `AVAILABLE` | CP3-D2 전 기본 `UNKNOWN`; 승인된 policy만 FRESH/STALE/EXPIRED 계산 | snapshot normalize 가능, latest atomic compare 가능 |
| timestamp null, positive price | `DEGRADED` | `UNKNOWN` | `missing_reasons.provider_timestamp=NOT_PROVIDED`; snapshot audit/normalize 가능, user-facing latest pointer 갱신 금지 |
| price missing/null | `UNAVAILABLE` | `UNKNOWN` | 0 대체 금지, PriceSnapshot 생성 금지, source/audit error만 기록 |
| currency mismatch/unknown | `DEGRADED` | `UNKNOWN` | raw/source 보존, normalized current publish와 latest 갱신 금지 |
| unresolved/unknown symbol | `UNAVAILABLE` | `UNKNOWN` | canonical security 가격 생성 금지 |
| schema error | `ERROR` | `UNKNOWN` | raw 보존, LKG/latest 유지 |

- `[OFFICIAL_DOC_CONTRACT]` provider `timestamp`는 null일 수 있고 `lastPrice`는 Decimal string 후보다.
- `[PROPOSED_REPO_CONTRACT]` `fetched_at`을 `observed_at`으로 복사하거나 timestamp null에 임의 date를 생성하지 않는다.
- `[USER_DECISION_REQUIRED]` FRESH/STALE/EXPIRED threshold와 market-calendar policy는 CP3-D2의 별도 live evidence 및 독립 승인 없이는 활성화하지 않는다.

### G.4 duplicate/revision/latest/history

- timestamp가 있으면 semantic key는 `(provider, provider_identity_id, provider_timestamp)`다.
- timestamp가 없으면 semantic key는 `(provider, provider_identity_id, source_version_id)`다. `fetched_at`을 자연키로 사용하지 않는다.
- `price_snapshot_id = "price_" + SHA-256("price-v1|" + semantic_key + "|" + normalized_content_hash)`.
- 같은 semantic key + 같은 normalized hash는 duplicate이며 새 normalized row/revision/latest write를 만들지 않는다. audit attempt는 남길 수 있다.
- 같은 semantic key + 다른 normalized hash는 new revision이다. 이전 snapshot을 보존하고 `supersedes_id`를 연결한다.
- current/latest state와 historical series는 분리한다. CP3에는 SQLite latest row 또는 pointer만 허용하며 누적 가격 history는 CP4 Parquet/DuckDB 범위다.
- 신규 오류, stale observation 또는 quarantined revision이 과거 정상 snapshot을 삭제하거나 latest pointer를 뒤로 이동시키지 못한다.

## H. raw → normalized → storage 추적성

### H.1 일곱 identity

| identity | 목적 | identity rule |
|---|---|---|
| collection attempt | 실행·실패·재시도 audit | 비결정적 attempt ID 허용; semantic hash에서 제외 |
| canonical request | method/path/query의 secret-free 의미 | exact canonical bytes SHA-256; symbol batch는 validate/deduplicate/ASCII sort |
| raw response payload | 받은 bytes와 status | canonical request ID + HTTP status + raw bytes hash |
| source version record | provider contract 아래의 immutable source version | raw response ID + provider contract version; revision link 별도 |
| normalized record | 한 entity/snapshot semantic version | dataset natural key + normalized semantic hash |
| latest-state pointer | dataset/entity별 last known-good | unique `(dataset, canonical entity ID)`; atomic conditional update |
| audit event | attempt outcome와 count/status | attempt ID 참조; raw/body/secret 없음 |

### H.2 raw manifest 최소 필드

- source system
- HTTP method
- allowlisted path template
- secret 없는 canonical query
- `fetched_at` aware UTC
- HTTP status
- allowlisted response metadata만: safe request ID 존재/값, numeric rate telemetry, content type
- `raw_content_hash` = exact raw bytes SHA-256
- opaque `raw_storage_ref`
- provider parser/contract version
- canonical request ID, raw response ID, source version ID

저장 금지: auth header/value, access token, client ID/secret, token request/response body, cookie, account header, raw absolute local path, unrestricted response headers, provider body의 로그 출력.

### H.3 crash safety

raw bytes는 temp file에 쓰고 가능한 범위에서 flush/fsync한 뒤 같은 volume atomic rename을 완료해야 한다. DB source manifest와 latest pointer는 durable raw ref가 확인된 뒤 transaction으로 publish한다. crash/partial write 시 manifest를 publish하지 않고 half-written file을 정상 input으로 사용하지 않는다.

## I. hash/idempotency/revision

### I.1 required cases

| case | result |
|---|---|
| 같은 request + 같은 raw hash | attempt audit 가능; raw/source/normalized duplicate 생성 금지 |
| 같은 request + 다른 raw hash | new raw/source version; 이전 version 보존; revision/supersession link |
| schema validation 실패 | raw/source version 보존; normalized/latest publish 금지; LKG 유지 |
| partial write/process crash | final manifest/latest publish 금지; orphan temp는 정상 data로 읽지 않음 |

### I.2 hash field set

`normalized_content_hash`에 포함:

- provider price/source contract version
- dataset name
- provider identity ID와 canonical security ID(있는 경우)
- provider symbol/market/security type/common/status/list/delist/ISIN 등 해당 normalized semantic fields
- price value, currency, provider timestamp
- explicit missing reasons
- mapping/lifecycle/revision semantic state
- parser/normalizer policy version

제외:

- collection attempt ID, run/job/audit ID
- `fetched_at`, DB inserted/updated time, wall-clock current time
- raw storage path/ref, source record ID, raw response ID
- latest pointer ID
- 현재 시각에 따라 변하는 calculated freshness
- log/request correlation ID

canonical JSON은 UTF-8, object key 정렬, insignificant whitespace 없음, Decimal string 보존, aware datetime UTC `Z`, NaN/Infinity 금지다. 비결정적 field 때문에 동일 semantic data의 hash가 달라지면 test 실패다.

### I.3 Phase 1 unique 제약 해결

- `[CURRENT_REPO_FACT]` 기존 `source_records(source_system, source_type, external_id)` unique를 수정하거나 timestamp suffix로 우회하지 않는다.
- `[PROPOSED_REPO_CONTRACT]` 신규 `provider_source_versions`는 `(canonical_request_id, http_status, raw_content_hash, provider_contract_version)` unique를 사용하고 self-FK `supersedes_id`를 둔다.
- `[PROPOSED_REPO_CONTRACT]` 기존 table은 Phase 1 fixture/source 전용으로 유지한다. provider latest와 revision은 신규 table/pointer에서 표현한다.

## J. versioned provider source contract — ADR-011 revised proposal

### J.1 field rules

| field | rule |
|---|---|
| `observed_at` | nullable aware UTC; provider가 timestamp를 제공할 때만 사용 |
| `observed_date` | nullable date-only; provider가 date를 제공할 때만 사용 |
| 둘 다 null | 허용하되 두 field의 structured missing reason 필수 |
| 둘 다 non-null | dataset policy가 명시적으로 허용할 때만; 서로 같은 의미로 합성 금지 |
| `published_at` | nullable aware UTC; null이면 structured missing reason 필수 |
| `fetched_at` | required aware UTC; body 수신 완료 시각 |
| contract version | provider source contract local Literal, 예: `toss-source/0.1.0`; 전역 `ContractVersion`과 분리 |

### J.2 dataset matrix

| dataset | observed_at | observed_date | both-null |
|---|---|---|---|
| stock discovery/detail | provider observation timestamp가 없으면 null | listDate/delistDate를 observation date로 대체하지 않음 | 허용 + `NOT_PROVIDED` reasons |
| current price | provider `timestamp`가 있으면 required | 금지 | timestamp null이면 허용 + reasons; freshness UNKNOWN |
| future daily flow | `updatedAt`이 실제 observation update timestamp일 때 허용 | provider `date` required | date까지 없으면 normalized publish 금지 |
| future candle | bar timestamp를 observed_at으로 사용 | trade date는 separate semantic date | both-value 허용 여부를 candle contract가 검증 |

- `[CURRENT_REPO_FACT]` 기존 `SourceRecord` v0.1.0은 그대로 유지한다.
- `[PROPOSED_REPO_CONTRACT]` 새 source contract는 별도 class/table/OpenAPI exposure 정책을 갖고 기존 fixture/API response를 바꾸지 않는다.
- `[USER_DECISION_REQUIRED]` ADR-011은 `PROPOSED — REVISED FOR CP3-A / AWAITING INDEPENDENT REVIEW`이며 승인 전 CP3-B 구현을 시작하지 않는다.

## K. DB migration/rollback

### K.1 CP3-B additive candidate

migration 후보명은 `0002_phase_02_cp3_foundation`이다. 이번 checkpoint에서는 만들지 않는다.

| candidate table | purpose/key |
|---|---|
| `provider_security_identities` | staging identity, immutable anchor digest, mapping/lifecycle state |
| `provider_identifier_history` | provider symbol/ISIN/market validity interval과 source version |
| `provider_identity_mappings` | staging → canonical issuer/security mapping status, evidence, approved event |
| `collection_attempts` | job outcome/count/status without secret/body |
| `canonical_requests` | deterministic secret-free request identity |
| `provider_source_versions` | raw/source version, hash, contract, supersession |
| `audit_events` | attempt/source/normalization publish audit |
| `current_price_latest` | verified security별 current snapshot payload 또는 latest pointer 하나 |

### K.2 constraints and rollback

- `0001_phase_01`에서 forward upgrade하고 기존 Phase 1 fixture row와 FK를 byte/semantic 보존한다.
- 신규 FK는 provider source/version과 staging/mapping/latest 사이에만 추가하고 기존 table destructive rebuild를 하지 않는다.
- anchor digest, provider identity history validity, source version unique, latest `(dataset, security_id)` unique를 명시한다.
- corp_code/CIK fake backfill, 기존 fixture 변환, 기존 `0001` 수정, SQLite 가격 history 누적을 금지한다.
- migration acceptance는 disposable DB에서 `upgrade → downgrade → re-upgrade`를 실행한다. production DB destructive downgrade는 금지한다.
- migration 중 실패하면 transaction rollback, unpublished manifest, LKG pointer를 유지한다.
- downgrade는 신규 metadata/pointer table만 제거할 수 있으나 실제 raw/history를 자동 삭제하지 않는다. 실제 DB에는 backup과 별도 승인 없이 실행하지 않는다.

## L. CP3-B/C/D checkpoint 분리

### CP3-B — Contract Foundation + Additive Migration + Raw/Source Trace

- provider-specific versioned contracts, source timestamp/date/missing semantics, enums
- additive migration, raw manifest/source metadata, repository interfaces
- offline fixtures/tests only
- application collection job와 live API 없음

### CP3-C — Security Master

- `/stocks/all` discovery DTO/fixture, `/stocks` detail DTO/fixture
- KR/US universe, identifier mapping, lifecycle, normalization, storage, idempotency
- unknown enum/collision negative test
- live API 없음

### CP3-D1 — Current Price Offline

- `/prices` DTO/fixture, 최대 200-symbol chunking
- Decimal/currency/timestamp-null/source trace/latest-state/idempotency/revision
- full offline regression

### CP3-D2 — Separately Approved Minimal Live Verification

- 사용자 별도 승인 전 실행 금지
- 승인된 소수 symbol만 `/stocks/all`과 `/prices` schema/header/timestamp semantics 최소 대조
- 값, body, token, raw header 저장 금지
- account/order endpoint와 header 금지

### CP3-D3 — Integrated QA and Closeout

- 전체 회귀, migration, idempotency, OpenAPI, production build, E2E, secret/policy
- false-green review, P0/P1/P2, 문서 closeout

각 checkpoint는 앞 checkpoint의 독립 검토와 사용자 승인 후에만 시작한다. CP3-A 완료 뒤 CP3-B로 자동 진행하지 않는다.

## M. acceptance test matrix

각 행은 test 목적, 입력, 기대 결과, 실패 severity, false-green 방지 방식을 계약한다. `P0`는 오매핑/secret/원본 훼손, `P1`은 핵심 계약·회귀 누락, `P2`는 비핵심 운영·설명 결함이다.

### M.1 CP3-B contract negative tests

| ID | 목적 | 입력 | 기대 결과 | severity | false-green 방지 |
|---|---|---|---|---|---|
| B-C01 | strict extra 금지 | valid payload + unknown field | validation error | P1 | exact error path와 extra field 이름 assert |
| B-C02 | float 유입 차단 | `lastPrice` JSON number | reject before Decimal conversion | P1 | Python float로 먼저 변환하지 않은 raw JSON test |
| B-C03 | exponent 차단 | `"1e3"` | reject | P1 | 일반 Decimal parser 성공 여부와 무관하게 grammar assert |
| B-C04 | naive time 차단 | offset 없는 timestamp | reject | P1 | expected exception type/message path assert |
| B-C05 | nullable timestamp 표현 | `timestamp=null` + reasons | provider source valid, freshness UNKNOWN | P1 | early return 금지; serialized fields assert |
| B-C06 | missing reason 강제 | null observed/published + reason 누락 | reject | P1 | 각 nullable field parameterized test |
| B-C07 | unknown market fail closed | new market token | raw/source only, normalized reject | P0 | default KR/US mapping 부재 assert |
| B-C08 | unknown securityType fail closed | unsupported/new token | quarantine, no canonical row | P0 | enum default/OTHER coercion 부재 assert |
| B-C09 | common/status contradiction | common=false 또는 status non-active인데 eligible flag | reject/quarantine | P0 | eligible/latest count remains zero assert |

### M.2 CP3-C mapping tests

| ID | 목적 | 입력 | 기대 결과 | severity | false-green 방지 |
|---|---|---|---|---|---|
| C-M01 | stable duplicate mapping | same symbol + same ISIN twice | same staging ID, one normalized version | P0 | row/ID/hash exact equality |
| C-M02 | ISIN change 감지 | same symbol + changed ISIN | revision/collision review, overwrite 없음 | P0 | old identifier/history still queryable |
| C-M03 | symbol change continuity | changed symbol + same unique ISIN | history interval update, internal ID 유지 | P0 | old/new identifier rows와 one canonical ID assert |
| C-M04 | duplicate ISIN 차단 | two active candidates same ISIN | both quarantine, auto merge 없음 | P0 | canonical row count zero |
| C-M05 | missing ISIN | null ISIN | UNRESOLVED + NOT_PROVIDED | P1 | empty string/default ID 부재 assert |
| C-M06 | ticker 재사용 분리 | delisted old + new listing same symbol | different staging identity | P0 | old history와 new anchor digest differ |
| C-M07 | name merge 금지 | same name, different symbol/ISIN | separate candidates | P0 | name index가 mapping authority 아님을 assert |
| C-M08 | 복수 share class | same issuer evidence + multiple classes | one issuer, distinct securities | P0 | distinct security IDs/identifier histories |
| C-M09 | regulator ID 부재 | KR no corp_code / US no CIK | staging UNRESOLVED, canonical issuer 없음 | P0 | Toss symbol/ticker가 regulatory field에 없음을 assert |

### M.3 CP3-C universe/lifecycle tests

| ID | 목적 | 입력 | 기대 결과 | severity | false-green 방지 |
|---|---|---|---|---|---|
| C-U01 | KR eligible path | KR/ACTIVE/supported common/KRW | eligible-for-mapping candidate | P1 | canonical publish와 candidate 상태를 구분 assert |
| C-U02 | US eligible path | US/ACTIVE/supported common/USD | eligible-for-mapping candidate | P1 | market/currency exact assert |
| C-U03 | non-common 제외 | common=false | excluded/quarantine | P0 | eligible count zero |
| C-U04 | unsupported security 제외 | ETF/ETN/preferred/warrant/fund/bond token | excluded/quarantine | P0 | COMMON default mapping 금지 assert |
| C-U05 | inactive 보존 | non-active detail | lifecycle event, no eligible/latest | P1 | prior verified history remains |
| C-U06 | discovery disappearance | prior candidate absent in next list | DISCOVERY_MISSING only | P0 | DELISTED/valid_to 자동 생성 부재 |
| C-U07 | unknown enum | new status/type/market token | raw preserved, normalized reject | P0 | test가 unknown을 known default로 patch하지 않음 |
| C-U08 | partial detail | requested 200 중 일부 response 누락 | missing subset quarantined, valid subset processed | P1 | empty collection PASS 금지, exact counts |

### M.4 CP3-D1 price tests

| ID | 목적 | 입력 | 기대 결과 | severity | false-green 방지 |
|---|---|---|---|---|---|
| D-P01 | valid Decimal | `"123.4500"` | exact Decimal/string roundtrip | P1 | binary float intermediate 사용 여부 검사 |
| D-P02 | 큰 Decimal | 구현 precision 경계의 매우 큰 canonical string | exact roundtrip 또는 documented fail-closed | P1 | float/scientific notation 금지 assert |
| D-P03 | zero semantics | `"0"` | DEGRADED quarantine, missing/AVAILABLE 아님 | P1 | latest pointer unchanged |
| D-P04 | negative 차단 | `"-1"`, `"-0"` | contract reject | P1 | exception swallow 금지 |
| D-P05 | offset normalization | valid non-UTC offset timestamp | exact UTC conversion, raw offset 보존 | P1 | expected instant equality assert |
| D-P06 | timestamp null | positive price + null timestamp | DEGRADED/UNKNOWN + reason, latest unchanged | P1 | fetched_at 복사 부재 assert |
| D-P07 | currency mismatch | KR+USD 또는 US+KRW | quarantine, publish 금지 | P0 | existing LKG unchanged |
| D-P08 | unknown symbol | response symbol not requested/mapped | reject/quarantine | P0 | synthetic security creation zero |
| D-P09 | exact duplicate | same request + same payload/hash | one source/normalized version, audit optional | P1 | row counts before/after exact |
| D-P10 | changed revision | same semantic key + changed price/hash | new revision + supersedes, prior preserved | P1 | both versions queryable |
| D-P11 | 200 chunk 경계 | 201 eligible symbols | batches 200+1, no loss/duplication | P1 | exact symbol multiset compare |
| D-P12 | partial batch | requested batch response subset | subset publish only, missing symbols UNAVAILABLE | P1 | expected request/response/publish counts |
| D-P13 | LKG 보존 | valid latest 후 schema/currency/timestamp-null error | previous latest remains | P0 | pointer ID equality before/after |

### M.5 CP3-B/D storage tests

| ID | 목적 | 입력 | 기대 결과 | severity | false-green 방지 |
|---|---|---|---|---|---|
| B-S01 | raw hash exactness | known byte sequence | expected SHA-256 exact match | P1 | reserialized JSON hash와 다름을 함께 assert |
| B-S02 | normalized hash 결정성 | same semantic fields, different run/fetched IDs | same hash | P1 | excluded field perturbation parameterized |
| B-S03 | repeated import idempotency | same manifests twice | second normalized insert/update zero | P1 | exact row counts/hash set |
| B-S04 | source revision | same request, different raw bytes | two source versions + link | P1 | timestamp suffix external ID 금지 assert |
| D-S05 | latest pointer atomicity | older/newer/revision sequence | only accepted LKG pointer | P0 | transaction rollback/failure injection |
| B-S06 | atomic raw failure | crash before rename/manifest | no published manifest/read | P0 | half-file 직접 생성 후 reader rejection |
| B-S07 | migration roundtrip | 0001 DB upgrade/downgrade/re-upgrade | constraints/data preserved | P1 | disposable path와 exact exit code |
| B-S08 | Phase 1 fixture 보존 | existing fixture DB before migration | IDs/payload/hash/API unchanged | P0 | pre/post canonical dump comparison |
| B-S09 | source natural-key 해결 | repeated price/revision inputs | 신규 provider table semantics 사용 | P1 | 기존 `source_records`에 clock suffix row 없음 |

### M.6 false-green gates — every checkpoint

| ID | 목적 | 입력 | 기대 결과 | severity | false-green 방지 |
|---|---|---|---|---|---|
| FG-01 | test 삭제/skip/xfail 금지 | git diff + collected tests | 삭제·신규 skip/xfail 0 | P1 | source scan + exact inventory |
| FG-02 | inventory 감소 금지 | full collection | backend ≥357, frontend exactly 43, E2E exactly 2; CP3 추가분은 증가 | P1 | 이름 목록과 count 둘 다 검증 |
| FG-03 | offline network 0 | standard suite | provider request 0 | P0 | socket deny + default/SelfTest counters |
| FG-04 | fixture/live 구분 | offline fixtures only | LIVE_VERIFIED 상태 변화 0 | P1 | docs/status diff scan |
| FG-05 | exception swallow 금지 | expected failure input | exact exception/assertion 실행 | P1 | pass-on-no-exception guard |
| FG-06 | empty collection 금지 | required nonempty fixtures | zero records이면 fail | P1 | explicit minimum counts |
| FG-07 | unknown default 금지 | unseen enum | reject/quarantine | P0 | default branch coverage와 row count zero |

## N. 비범위와 보안

CP3-A 및 후속 별도 승인 전 계속 금지:

- 실제 주문, 모의주문, 자동매매
- account/holding/order/conditional-order endpoint와 `X-Tossinvest-Account`
- WebSocket
- browser Toss API 호출
- credential/token/auth body의 DB/Git/log/raw/fixture/QA 저장
- OpenDART, SEC/13F, news, macro, OpenAI API
- UI, scheduler, live polling
- 신규 provider dependency
- exact callable allowlist 확대
- 실제 credential 요청/조회/사용 또는 CP3 live call

## O. unresolved decision과 conservative default

| decision | 상태 | conservative default |
|---|---|---|
| ADR-011 nullable provider source time | `[USER_DECISION_REQUIRED]` revised PROPOSED | 기존 SourceRecord 유지, provider normalized publish 시작 금지 |
| ADR-012 provider staging identity | `[USER_DECISION_REQUIRED]` PROPOSED | canonical Issuer/Security 자동 생성 금지 |
| exact provider securityType enum mapping | `[LIVE_UNVERIFIED]` + independent evidence required | unknown 전부 quarantine |
| 신규 canonical ID/promotion authority | `[USER_DECISION_REQUIRED]` | staging UNRESOLVED 유지 |
| exchange mapping | `[LIVE_UNVERIFIED]` | exchange 추정 금지, canonical promotion 금지 |
| timestamp-null current publication | `[PROPOSED_REPO_CONTRACT]` | DEGRADED/UNKNOWN, latest pointer 갱신 금지 |
| freshness thresholds | `[USER_DECISION_REQUIRED]` after minimal live evidence | 항상 UNKNOWN |
| SQLite current payload vs pointer | `[USER_DECISION_REQUIRED]` CP3-B schema review | history 금지, 최소 latest pointer 우선 |

## checkpoint 판정

- CP1: `PASS`
- CP2: `COMPLETE`
- CP3-A: `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`
- CP3-B: `NOT STARTED`
- Phase 2: `IMPLEMENTATION IN PROGRESS`

CP3-A는 application implementation 0, fixture/test/migration/dependency 변경 0, actual credential/API usage 0을 전제로 한다. 독립 검토와 사용자 승인 전에는 이 문서의 제안을 `ACCEPTED`, `PASS` 또는 runtime contract로 표시하지 않는다.
