# Phase 2 CP3-A — Security Master + Current Price 계획·계약

- 문서 상태: `PASS — CONTRACT APPROVED AND CLOSED`
- 작성일: `2026-08-24`, 독립검증 보완·승인일: `2026-08-25` (`Asia/Seoul`)
- 기준 브랜치: `feature/phase-02-toss`
- 시작 commit: `6bd5d2ae9c26f02f2cd4bd75a474633a9082fa16`
- 독립검증 보완 시작 commit: `386a0b2fe7bd18ed4b662eb2695ff85cc2a08cd3`
- checkpoint 경계: `CP3-A documentation/contract only`
- 후속 상태: `CP3-B REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW / CP3-C NOT STARTED`

이 문서는 GPT independent re-review `PASS WITH CLOSEOUT CONDITION`과 2026-08-25 사용자 승인으로 확정된 CP3-A repository contract다. 이 승인은 CP3-B application 구현 승인, live endpoint 검증 또는 Phase 2 완료를 뜻하지 않는다.

## 근거 표기

| 표기 | 의미 |
|---|---|
| `[CURRENT_REPO_FACT]` | 현재 commit의 문서, 계약, ORM, migration 또는 connector code에서 직접 확인한 사실 |
| `[OFFICIAL_DOC_CONTRACT]` | 저장소의 2026-08-23 canonical Toss OpenAPI 조사 기록에 근거한 공개 provider 계약 |
| `[LIVE_VERIFIED]` | 2026-08-24 CP2-D2의 redacted one-shot 결과로 실제 확인한 최소 범위 |
| `[LIVE_UNVERIFIED]` | 공식 계약 또는 계획은 있으나 해당 endpoint/field/semantics를 실제 응답으로 확인하지 않은 범위 |
| `[REPO_CONTRACT]` | 독립검증과 2026-08-25 사용자 승인을 거친 CP3-A 저장소 계약 |
| `[USER_DECISION_REQUIRED]` | 구현 전에 독립 검토와 사용자의 명시적 결정이 필요한 항목 |

각 결정은 위 근거를 명시한다. 서로 다른 근거가 한 행에 있으면 확인된 사실과 제안 범위를 문장으로 분리한다.

## A. 목적과 범위

- `[CURRENT_REPO_FACT]` Phase 1 `SourceRecord`, `Issuer`, `Security`, `PriceBar` v0.1.0과 SQLite `0001_phase_01`이 존재한다.
- `[CURRENT_REPO_FACT]` CP2는 exact REST allowlist, memory-only OAuth token, bounded retry, offline/live 경계를 구현했고 `COMPLETE`다.
- `[LIVE_VERIFIED]` canonical provider contract drift 없음, OpenAPI `3.1.0`, provider REST `1.2.14`, actual OAuth issuance, credential acceptance, allowed-IP 실행 경로, `GET /api/v1/stocks`, 성공 응답의 Limit/Remaining/Reset rate header만 확인됐다.
- `[LIVE_UNVERIFIED]` `/api/v1/stocks/all`, `/api/v1/prices`, 전체 market/enum/null/freshness semantics, natural 429와 actual 429/5xx는 확인되지 않았다.
- `[REPO_CONTRACT]` CP3-A는 Security Master와 Current Price의 endpoint 역할, identity, lifecycle, source trace, idempotency, additive migration, offline acceptance를 계약화한다. application, test, fixture, migration, dependency, runtime config, route 또는 collection job은 만들지 않는다.
- `[CURRENT_REPO_FACT]` 독립검증 결과는 `CHANGES REQUIRED`, P0 0/P1 2였고 CP3-B는 승인되지 않았다. P1-01은 canonical mapping 전제의 순환 의존, P1-02는 최초 allocation 뒤 identifier enrichment reconciliation 부재다.
- `[REPO_CONTRACT]` approved revision은 provider-scoped price storage와 canonical current-price view를 분리하고, 최초 allocation 전 continuity-first reconciliation을 수행해 P1-01/P1-02를 닫는다.

## B. Phase 1 계약과의 호환성

### B.1 보존할 계약

- `[CURRENT_REPO_FACT]` 전역 `ContractVersion`은 `Literal["0.1.0"]`이고 `StrictContract`는 `extra="forbid"`, canonical Decimal string, aware UTC를 강제한다.
- `[CURRENT_REPO_FACT]` `Issuer`는 KR `corp_code`, US `cik`를 강제한다. 오류 문구가 synthetic identifier를 언급하지만 이는 Phase 1 합성 fixture 조건이며 실제 Toss symbol을 그 필드에 넣을 근거가 아니다.
- `[CURRENT_REPO_FACT]` `Security`는 `issuer_id`, `exchange`, `ticker`, `share_class`, `currency`를 요구하고 `mapping_status`는 `VERIFIED|UNRESOLVED`다.
- `[CURRENT_REPO_FACT]` `SourceRecord` v0.1.0은 `observed_at`, `published_at`, `fetched_at`을 모두 required aware datetime으로 요구한다.
- `[CURRENT_REPO_FACT]` `source_records`에는 `(source_system, source_type, external_id)` unique 제약이 있어 같은 자연키의 반복 가격 payload와 revision을 한 행 집합으로 표현할 수 없다.
- `[REPO_CONTRACT]` 위 계약, Phase 1 fixture/API/OpenAPI, `0001_phase_01`과 기존 row는 수정·완화·backfill하지 않는다. 신규 provider staging/source 계약은 별도 version과 additive table을 사용한다.

### B.2 현재 문서·코드 충돌과 disposition

| 충돌 | 영향 | disposition |
|---|---|---|
| `[CURRENT_REPO_FACT]` `docs/04` SecurityMaster 예시는 `corp_code=null`, `cik=null`, `mapping_status=VERIFIED`지만 실제 `Issuer` validator는 jurisdiction별 regulatory ID를 강제 | Toss만으로 canonical issuer를 만들면 거짓 ID 또는 validation 실패; canonical mapping을 price storage의 필수조건으로 두면 Phase 2가 Phase 3/4에 순환 의존 | `[REPO_CONTRACT]` provider staging identity에서 `mapping_status=UNRESOLVED`, explicit missing reason을 사용한다. valid provider identity의 provider-scoped price는 저장할 수 있지만 canonical Security/company price publish는 verified mapping 전까지 금지한다. |
| `[CURRENT_REPO_FACT]` `Security.exchange` required이나 현재 CP3 근거에는 Toss exchange semantics가 확정돼 있지 않음 | 임의 exchange 생성 위험 | `[REPO_CONTRACT]` exchange가 검증될 때까지 staging 유지 |
| `[CURRENT_REPO_FACT]` `SourceRecord` 관측/발표 시각 required, `[OFFICIAL_DOC_CONTRACT]` price timestamp nullable | fetch 시각을 관측시각으로 위조할 위험 | `[REPO_CONTRACT]` accepted ADR-011 provider source contract 사용 |
| `[CURRENT_REPO_FACT]` Phase 1 source unique key는 revision 불가 | timestamp suffix로 멱등성을 회피할 위험 | `[REPO_CONTRACT]` 신규 provider source-version table과 latest pointer로 분리 |

## C. Toss endpoint 역할

### C.1 `GET /api/v1/stocks/all`

- `[OFFICIAL_DOC_CONTRACT]` `market`을 받아 KR/US universe 목록을 반환하는 discovery endpoint다.
- `[LIVE_UNVERIFIED]` 실제 KR/US body, 목록 완전성, enum/null semantics는 확인하지 않았다.
- `[REPO_CONTRACT]` KR과 US를 별도 canonical request로 조회한다. 최초 범위는 `ACTIVE`, common share, 명시적으로 지원된 stock type 후보뿐이다.
- `[REPO_CONTRACT]` discovery 후보 생성 전용이다. 상세 Security Master의 단독 최종 source로 사용하지 않는다.
- `[REPO_CONTRACT]` 이전 목록에서 사라진 것은 `DISCOVERY_MISSING` observation일 뿐 `INACTIVE` 또는 `DELISTED`가 아니다.

### C.2 `GET /api/v1/stocks`

- `[OFFICIAL_DOC_CONTRACT]` `symbols` 1~200개를 쉼표로 전달하고 `symbol`, `name`, `englishName`, `isinCode`, `market`, `securityType`, `isCommonShare`, `status`, `currency`, `listDate`, `delistDate`, `sharesOutstanding`, `leverageFactor`, `koreanMarketDetail`을 제공하는 detail 후보 endpoint다.
- `[LIVE_VERIFIED]` actual OAuth 뒤 이 endpoint를 호출하는 구조와 성공 response outer structure만 확인됐다.
- `[LIVE_UNVERIFIED]` 전체 market, enum, nullable field, ISIN, status/list/delist semantics는 검증되지 않았다.
- `[REPO_CONTRACT]` discovery 후보를 최대 200 symbols씩 detail-enrich한다. response에 누락된 후보는 `PARTIAL_DETAIL`로 격리하고 빈 값으로 채우지 않는다.

### C.3 `GET /api/v1/prices`

- `[OFFICIAL_DOC_CONTRACT]` `symbols` 1~200개와 `symbol`, nullable `timestamp`, Decimal string `lastPrice`, `currency`를 사용한다.
- `[LIVE_UNVERIFIED]` endpoint body, timestamp-null 빈도와 의미, 가격/currency semantics는 실제 확인하지 않았다.
- `[REPO_CONTRACT]` discovery/detail 검증을 통과한 valid provider identity 중 lifecycle/currency가 price-eligible이고 collision/quarantine 상태가 아닌 identity만 요청한다. canonical `security_id` 존재는 provider-scoped 요청·저장의 필수조건이 아니다.
- `[REPO_CONTRACT]` canonical mapping이 `UNRESOLVED`여도 `provider_security_identity_id`에 귀속된 `ProviderPriceSnapshot`과 provider-scoped latest state는 저장할 수 있다.
- `[REPO_CONTRACT]` canonical current-price view는 `security_id` linkage가 `VERIFIED`일 때만 생성·노출한다. unresolved provider price를 canonical company price, issuer-level analysis, OpenDART/SEC/13F 결합 또는 canonical Security API의 verified price로 표현하지 않는다.
- `[REPO_CONTRACT]` quarantined, collision, stale provider identity에는 provider-scoped normalized snapshot/latest도 publish하지 않는다.

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
- `[REPO_CONTRACT]` CP3-B는 저장된 canonical contract evidence로 common-stock exact token을 먼저 고정해야 하며, 확인 전에는 symbolic 추정값을 runtime allowlist로 만들 수 없다. 확인되지 않은 값은 항상 fail closed한다.
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

`ELIGIBLE_FOR_MAPPING`은 canonical mapping `VERIFIED`와 다르다. 이것만으로 canonical current-price publish 권한을 주지는 않지만, 별도 `PROVIDER_PRICE_ELIGIBLE` 검증에서 valid identity, supported lifecycle/type/common-share, currency 일치와 collision/quarantine 부재를 모두 확인하면 provider-scoped price 요청·저장은 허용할 수 있다.

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

- `[REPO_CONTRACT]` accepted ADR-012에 따라 `provider_security_identity`와 canonical `Issuer`/`Security`를 분리한다.
- `[REPO_CONTRACT]` staging row는 nullable `issuer_id`/`security_id`, `mapping_status=UNRESOLVED`, `missing_reasons.issuer_id=UNRESOLVED`, 필요 시 `missing_reasons.security_id=UNRESOLVED`를 가진다.
- `[REPO_CONTRACT]` OpenDART corp_code 또는 SEC CIK와 instrument mapping이 승인될 때만 canonical mapping event를 만들 수 있다.
- `[REPO_CONTRACT]` provider identity의 유효성과 canonical mapping 상태는 독립 축이다. valid·non-collision·non-quarantine provider identity는 canonical linkage 없이 provider-scoped price를 소유할 수 있다. 이후 승인된 mapping은 nullable `security_id` linkage만 추가하며 provider identity 또는 price history를 rekey하지 않는다.

### E.3 exact continuity-first reconciliation and ID allocation algorithm

문자열은 UTF-8, separator `|`, Unicode NFC, provider symbol의 case는 원문을 보존하되 provider가 명시한 canonical case만 사용한다. 임의 upper/lower 변환은 하지 않는다.

1. `canonical_request_id = "treq_" + sha256(method|path_template|canonical_query)`의 64 lowercase hex를 계산하고 신규 observation과 source version을 보존한다.
2. anchor 우선순위를 적용하기 전에 같은 provider/market의 active identity와 append-only `provider_identifier_history`에서 continuity 후보를 검색한다. evidence는 exact active symbol interval, unique valid ISIN history, exact listDate history, lifecycle interval과 source lineage이며 name-only 유사성은 evidence가 아니다.
3. 서로 모순되지 않는 continuity evidence가 기존 identity 하나만 deterministic하게 가리키면 그 `provider_security_identity_id`를 재사용한다.
4. 후속 ISIN/listDate/symbol은 기존 identity의 identifier history에 source version, `valid_from`, revision reason을 가진 enrichment/revision으로 추가한다. 기존 immutable allocation anchor와 ID는 변경하지 않는다.
5. continuity evidence가 둘 이상의 기존 identity를 가리키거나 신규 identifier가 다른 active identity의 unique identifier와 충돌하면 자동 merge, 임의 winner 선택과 새 identity 생성을 모두 금지한다. observation을 `UNRESOLVED_COLLISION`으로 표시하고 관련 identity/price publish를 `QUARANTINE`한다.
6. 기존 continuity evidence가 전혀 없을 때만 최초 allocation을 수행한다. 최초 anchor 우선순위는 다음과 같다.
   - unique·valid ISIN: `toss-identity-v1|market|ISIN|isin`;
   - ISIN이 없고 non-null list date가 있으면: `toss-identity-v1|market|SYMBOL_LIST_DATE|symbol|listDate`;
   - 둘 다 없으면 최초 valid raw/source observation: `toss-identity-v1|market|FIRST_SEEN_RAW|symbol|raw_content_hash`.
7. `provider_security_identity_id = "tpsi_" + SHA-256(anchor)` 전체 64 lowercase hex다. 같은 최초 anchor는 항상 같은 ID를 반환한다. full digest가 다른 anchor와 충돌하면 suffix나 현재 시각을 붙이지 않고 `BLOCKED_COLLISION`으로 중단한다.
8. 최초 allocation 뒤 더 높은 우선순위 identifier가 나타나도 anchor migration/rekey/ID 재발급을 금지한다. allocation registry는 original anchor, full digest, first source version, enrichment와 mapping history를 영구 보존한다.
9. deterministic rebuild는 append-only raw/source manifest를 `(fetched_at, source_version_id)`로 stable sort한 뒤 각 observation에 위 continuity-first algorithm을 순서대로 replay한다. 기존 approved mapping event도 linkage evidence로 replay하되 provider ID나 allocation anchor를 대체하지 않는다.
10. approved canonical mapping event는 nullable `issuer_id`/`security_id` linkage와 `mapping_status=VERIFIED`만 추가한다. provider identity와 기존 provider price history ID/hash를 변경하거나 rekey하지 않는다.
11. 기존 Phase 1 `issuer_id`/`security_id`는 grandfathered ID로 그대로 둔다.
12. 신규 canonical issuer는 승인된 regulatory anchor만 허용한다: `issuer-v1|KR|CORP_CODE|corp_code` 또는 `issuer-v1|US|CIK|cik`; `issuer_id = "issuer_" + SHA-256(anchor)`.
13. 신규 canonical security는 승인된 mapping event의 immutable anchor `security-v1|issuer_id|instrument_identifier_kind|instrument_identifier`로 `security_id = "sec_" + SHA-256(anchor)`를 만든다. ISIN이 후일 변경돼도 ID를 재발급하지 않고 identifier history/revision을 추가한다.
14. canonical anchor collision, duplicate active ISIN 또는 서로 다른 issuer 후보는 자동 병합하지 않고 `UNRESOLVED_COLLISION`으로 격리한다.

- `[REPO_CONTRACT]` 위 continuity-first provider identity algorithm과 enrichment/no-rekey/collision 규칙은 accepted ADR-012의 runtime 구현 계약이다.
- `[USER_DECISION_REQUIRED]` canonical issuer/security promotion의 구체적 authority와 external evidence는 CP3-C 구현 전에 별도 승인해야 한다. 이는 accepted provider identity algorithm을 완화하지 않는다.

### E.4 identifier history cases

| case | required behavior |
|---|---|
| ISIN null → valid ISIN 등장 | exact symbol/lifecycle continuity가 기존 identity 하나를 가리키면 같은 ID 유지, ISIN enrichment history 추가, anchor/rekey/new identity 0 |
| listDate null → valid listDate 등장 | exact continuity가 하나이면 같은 ID 유지, listDate enrichment history 추가, anchor/rekey 0 |
| ISIN/listDate 둘 다 null → 이후 둘 다 등장 | 기존 first-seen identity를 먼저 찾고 두 identifier를 같은 identity history에 추가; 최초 priority 재적용·새 ID 생성 금지 |
| 동일 symbol + identifier enrichment | active interval과 다른 evidence가 모순되지 않고 후보 하나이면 기존 ID 재사용 |
| enrichment가 다른 active identity와 충돌 | 자동 merge/new identity/winner 선택 0; `UNRESOLVED_COLLISION` + 관련 price `QUARANTINE` |
| symbol 변경 + 같은 verified ISIN | 기존 provider identity/internal ID 유지, old symbol `valid_to`, new symbol `valid_from`, mapping review event |
| 같은 symbol + ISIN 변경 | 자동 overwrite 금지; share/class/corporate-action evidence 전까지 신규 candidate 또는 collision quarantine |
| symbol 재사용 | old lifecycle close 후 별도 staging identity; old ID 부활 금지 |
| ISIN missing | explicit `NOT_PROVIDED`; name-only promotion 금지 |
| ISIN change | old value history 보존, source revision과 mapping review 필수 |
| ISIN collision | 모든 관련 candidate quarantine; 하나를 임의 winner로 선택 금지 |
| ISIN correction | 기존 값과 correction evidence를 모두 history로 보존; unique continuity가 하나일 때만 같은 ID 유지, 다른 active identity와 충돌하면 quarantine |
| duplicate active ISIN | 관련 active identity 모두 `UNRESOLVED_COLLISION`; 자동 merge와 canonical/provider price publish 금지 |
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

- `[REPO_CONTRACT]` lifecycle은 observation history이며 단일 discovery snapshot의 부재를 사실로 승격하지 않는다.
- `[LIVE_UNVERIFIED]` provider status/delist transition semantics는 CP3-D2 전까지 live verified가 아니다.

## G. Current Price 계약

### G.1 `ProviderPriceSnapshot` field contract

`ProviderPriceSnapshot`은 Toss가 직접 식별한 provider instrument의 provider-scoped normalized price다. canonical `Issuer`/`Security`와 별도 identity를 가지며 Phase 2에서 Phase 3 OpenDART corp_code 또는 Phase 4 SEC CIK 없이 저장할 수 있다.

| field | type/rule |
|---|---|
| `price_snapshot_id` | deterministic `SafeId`; semantic key + normalized hash로 생성 |
| `provider_security_identity_id` | required immutable provider identity ID; valid·non-collision·non-quarantine identity만 허용 |
| `provider_symbol` | source spelling을 보존한 provider-scoped identifier |
| `last_price` | canonical non-exponent Decimal JSON string; binary float/JSON number 금지 |
| `currency` | provider response exact value를 보존하고 internal exact enum과 별도 검증 |
| `provider_timestamp` | nullable aware provider timestamp; normalized value는 UTC |
| `fetched_at` | required aware UTC response-complete time |
| `source_version_id` | required immutable provider source-version record ID |
| `raw_content_hash` | exact response raw bytes SHA-256 |
| `normalized_content_hash` | 아래 semantic field set의 canonical SHA-256 |
| `provider_contract_version` | provider price contract 전용 version; 전역 v0.1.0 Literal과 분리 |
| `freshness_status` | `FRESH|STALE|EXPIRED|UNKNOWN`; timestamp null이면 반드시 `UNKNOWN` |
| `availability_status` | `AVAILABLE|DEGRADED|ERROR|UNAVAILABLE` |
| `revision_status` | `ORIGINAL|AMENDED|SUPERSEDED`; duplicate는 신규 revision이 아님 |
| `security_id` | optional canonical linkage; 없으면 null이며 가짜 ID 생성 금지 |
| `canonical_mapping_status` | optional linkage state `UNRESOLVED|VERIFIED`; `security_id=null`이면 `VERIFIED` 금지 |

### G.2 canonical current-price view

- canonical current-price view는 `ProviderPriceSnapshot`을 복사·rekey한 별도 history가 아니라 verified linkage를 통해 조회하는 projection이다.
- `security_id`가 non-null이고 `canonical_mapping_status=VERIFIED`이며 provider snapshot 자체가 publish-eligible일 때만 생성·노출한다.
- mapping이 `UNRESOLVED`이면 provider-scoped storage/latest는 가능하지만 canonical view row/count, canonical Security API price, issuer/company analysis 연결은 모두 0이다.
- 후속 approved mapping은 linkage만 추가한다. 기존 `provider_security_identity_id`, `price_snapshot_id`, source/hash/revision chain과 historical rows를 변경하지 않는다.
- mapping 취소·충돌 시 canonical projection을 중지하되 provider source/history를 삭제하지 않는다.

### G.3 Decimal rules

- 허용 grammar: `0` 또는 `[1-9][0-9]*(\.[0-9]+)?`; leading plus, leading zero, exponent, NaN, Infinity, whitespace, JSON number와 binary float를 거부한다.
- `last_price > 0`일 때만 active common provider identity의 provider-scoped current/latest publish 후보가 된다. canonical view에는 별도 verified mapping 조건이 추가된다.
- exact string `0`은 missing으로 바꾸지 않지만 `NON_POSITIVE_PRICE` quality flag와 `DEGRADED` quarantine으로 처리해 latest pointer를 갱신하지 않는다.
- 음수와 `-0`은 contract error로 reject한다.
- 규모 상한을 binary float로 두지 않는다. storage length/Decimal precision 한계는 CP3-D1 test에서 explicit arbitrary-precision boundary로 정한다.

### G.4 timestamp/null/freshness/availability

| input state | availability | freshness | normalized/latest behavior |
|---|---|---|---|
| valid provider identity, positive price, currency match, aware timestamp | `AVAILABLE` | CP3-D2 전 기본 `UNKNOWN`; 승인된 policy만 FRESH/STALE/EXPIRED 계산 | provider snapshot normalize와 provider latest atomic compare 가능; canonical view는 verified linkage 필요 |
| timestamp null, positive price | `DEGRADED` | `UNKNOWN` | `missing_reasons.provider_timestamp=NOT_PROVIDED`; snapshot audit/normalize 가능, user-facing latest pointer 갱신 금지 |
| price missing/null | `UNAVAILABLE` | `UNKNOWN` | 0 대체 금지, ProviderPriceSnapshot 생성 금지, source/audit error만 기록 |
| currency mismatch/unknown | `DEGRADED` | `UNKNOWN` | raw/source 보존, normalized current publish와 latest 갱신 금지 |
| valid provider identity + canonical mapping unresolved | provider price 조건에 따름 | provider timestamp 조건에 따름 | provider snapshot/latest 가능; canonical view와 issuer/company analysis 0 |
| unknown provider symbol, identity collision/quarantine | `UNAVAILABLE` | `UNKNOWN` | provider snapshot/latest와 canonical view 모두 금지 |
| schema error | `ERROR` | `UNKNOWN` | raw 보존, LKG/latest 유지 |

- `[OFFICIAL_DOC_CONTRACT]` provider `timestamp`는 null일 수 있고 `lastPrice`는 Decimal string 후보다.
- `[REPO_CONTRACT]` `fetched_at`을 `observed_at`으로 복사하거나 timestamp null에 임의 date를 생성하지 않는다.
- `[USER_DECISION_REQUIRED]` FRESH/STALE/EXPIRED threshold와 market-calendar policy는 CP3-D2의 별도 live evidence 및 독립 승인 없이는 활성화하지 않는다.

### G.5 duplicate/revision/latest/history

- timestamp가 있으면 semantic key는 `(provider, provider_identity_id, provider_timestamp)`다.
- timestamp가 없으면 semantic key는 `(provider, provider_identity_id, source_version_id)`다. `fetched_at`을 자연키로 사용하지 않는다.
- `price_snapshot_id = "price_" + SHA-256("price-v1|" + semantic_key + "|" + normalized_content_hash)`.
- 같은 semantic key + 같은 normalized hash는 duplicate이며 새 normalized row/revision/latest write를 만들지 않는다. audit attempt는 남길 수 있다.
- 같은 semantic key + 다른 normalized hash는 new revision이다. 이전 snapshot을 보존하고 `supersedes_id`를 연결한다.
- current/latest state와 historical series는 분리한다. CP3에는 SQLite provider-scoped latest row 또는 pointer만 허용하며 canonical current-price는 verified mapping projection으로 제공한다. 누적 가격 history는 CP4 Parquet/DuckDB 범위다.
- 신규 오류, stale observation 또는 quarantined revision이 과거 정상 snapshot을 삭제하거나 latest pointer를 뒤로 이동시키지 못한다.
- canonical mapping linkage의 추가·취소는 provider snapshot normalized hash/revision을 바꾸지 않는다. mapping event는 별도 identity/history로 보존한다.

## H. raw → normalized → storage 추적성

### H.1 일곱 identity

| identity | 목적 | identity rule |
|---|---|---|
| collection attempt | 실행·실패·재시도 audit | 비결정적 attempt ID 허용; semantic hash에서 제외 |
| canonical request | method/path/query의 secret-free 의미 | exact canonical bytes SHA-256; symbol batch는 validate/deduplicate/ASCII sort |
| raw response payload | 받은 bytes와 status | canonical request ID + HTTP status + raw bytes hash |
| source version record | provider contract 아래의 immutable source version | raw response ID + provider contract version; revision link 별도 |
| normalized record | 한 entity/snapshot semantic version | dataset natural key + normalized semantic hash |
| latest-state pointer | dataset/provider entity별 last known-good | provider price는 unique `(dataset, provider_security_identity_id)`; canonical view는 verified linkage projection; atomic conditional update |
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

raw bytes는 temp file에 쓰고 가능한 범위에서 flush/fsync한 뒤 target을 교체할 수 없는 atomic no-replace publish를 완료해야 한다. 경쟁 writer가 먼저 만든 같은 bytes/hash는 dedupe하고 다른/corrupt bytes는 conflict로 차단하며 기존 target을 overwrite하지 않는다. DB source manifest와 latest pointer는 durable raw ref가 확인된 뒤 transaction으로 publish한다. crash/partial write 시 manifest를 publish하지 않고 half-written file을 정상 input으로 사용하지 않는다.

## I. hash/idempotency/revision

### I.1 required cases

| case | result |
|---|---|
| 같은 request + 같은 raw hash | attempt audit 가능; raw/source/normalized duplicate 생성 금지 |
| 같은 request + 다른 raw hash | new raw/source version; 이전 version 보존; revision/supersession link |
| schema validation 실패 | raw/source version 보존; normalized/latest publish 금지; LKG 유지 |
| partial write/process crash | final manifest/latest publish 금지; orphan temp는 정상 data로 읽지 않음 |

### I.2 hash field set

provider instrument와 `ProviderPriceSnapshot`의 `normalized_content_hash`에 포함:

- provider price/source contract version
- dataset name
- provider identity ID
- provider symbol/market/security type/common/status/list/delist/ISIN 등 해당 normalized semantic fields
- price value, currency, provider timestamp
- explicit missing reasons
- provider lifecycle/revision semantic state
- parser/normalizer policy version

제외:

- collection attempt ID, run/job/audit ID
- `fetched_at`, DB inserted/updated time, wall-clock current time
- raw storage path/ref, source record ID, raw response ID
- latest pointer ID
- 현재 시각에 따라 변하는 calculated freshness
- log/request correlation ID
- nullable canonical `security_id`, canonical mapping status/event/evidence; 이것들은 별도 mapping record/hash에 포함하며 provider price history를 rekey하지 않음

canonical JSON은 UTF-8, object key 정렬, insignificant whitespace 없음, Decimal string 보존, aware datetime UTC `Z`, NaN/Infinity 금지다. 비결정적 field 때문에 동일 semantic data의 hash가 달라지면 test 실패다.

### I.3 Phase 1 unique 제약 해결

- `[CURRENT_REPO_FACT]` 기존 `source_records(source_system, source_type, external_id)` unique를 수정하거나 timestamp suffix로 우회하지 않는다.
- `[REPO_CONTRACT]` 신규 `provider_source_versions`는 `(canonical_request_id, http_status, raw_content_hash, provider_contract_version)` unique를 사용하고 self-FK `supersedes_id`를 둔다.
- `[REPO_CONTRACT]` 기존 table은 Phase 1 fixture/source 전용으로 유지한다. provider latest와 revision은 신규 table/pointer에서 표현한다.

## J. versioned provider source contract — accepted ADR-011

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
- `[REPO_CONTRACT]` 새 source contract는 별도 class/table/OpenAPI exposure 정책을 갖고 기존 fixture/API response를 바꾸지 않는다.
- `[REPO_CONTRACT]` ADR-011은 2026-08-25 `ACCEPTED`다. 이 결정은 CP3-B 시작 권한이 아니며 별도 명시적 authorization 전에는 구현하지 않는다.

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
| `provider_current_price_latest` | valid provider identity별 current snapshot payload 또는 latest pointer 하나; canonical mapping nullable |
| canonical current-price view | 별도 history table이 아닌 verified provider→security linkage projection 후보 |

### K.2 constraints and rollback

- `0001_phase_01`에서 forward upgrade하고 기존 Phase 1 fixture row와 FK를 byte/semantic 보존한다.
- 신규 FK는 provider source/version과 staging/mapping/latest 사이에만 추가하고 기존 table destructive rebuild를 하지 않는다.
- anchor digest, provider identity history validity, source version unique, provider latest `(dataset, provider_security_identity_id)` unique를 명시한다. canonical linkage unique/validity는 mapping table에서 별도 검증한다.
- corp_code/CIK fake backfill, 기존 fixture 변환, 기존 `0001` 수정, SQLite 가격 history 누적을 금지한다.
- migration acceptance는 disposable DB에서 `upgrade → downgrade → re-upgrade`를 실행한다. production DB destructive downgrade는 금지한다.
- migration 중 실패하면 transaction rollback, unpublished manifest, LKG pointer를 유지한다.
- downgrade는 신규 metadata/pointer table만 제거할 수 있으나 실제 raw/history를 자동 삭제하지 않는다. 실제 DB에는 backup과 별도 승인 없이 실행하지 않는다.

### K.3 CP3-B implementation record — 2026-08-25

- `[CURRENT_REPO_FACT]` `0002_phase_02_cp3_foundation`은 `0001_phase_01`을 정확히 parent로 사용하며 기존 table/column을 수정하지 않고 9개 provider metadata/pointer table만 추가한다.
- `[CURRENT_REPO_FACT]` `canonical_requests`, `provider_raw_manifests`, `provider_source_versions`, `collection_attempts`, `provider_audit_events`, `provider_security_identities`, `provider_identifier_history`, `provider_identity_mappings`, `provider_latest_pointers`를 구현했다.
- `[CURRENT_REPO_FACT]` disposable DB에서 blank upgrade, 기존 Phase 1 fixture DB upgrade, CP3 downgrade/re-upgrade, migration failure, FK/unique/self-FK/check constraint와 Phase 1 row/hash/payload 보존을 offline test로 검증한다.
- `[CURRENT_REPO_FACT]` latest table은 `(dataset, provider_security_identity_id)` unique pointer foundation뿐이며 가격 history 또는 `ProviderPriceSnapshot` payload를 저장하지 않는다.
- `[CURRENT_REPO_FACT]` 독립검증 hardening은 later-fetch telemetry를 semantic identity에서 제외하되 dataset/parser/normalized hash/revision link 충돌을 차단하고, exact path→dataset/request→raw→source→attempt/audit graph를 repository에서 검증한다.
- `[CURRENT_REPO_FACT]` VERIFIED mapping은 active non-quarantined identity, 실제 issuer/security 관계와 identity source lineage evidence를 요구한다. provider latest는 one-statement conditional SQL update를 사용하며 CURRENT_PRICE freshness는 CP3-D2 전 `UNKNOWN`, timestamp-null source는 latest-ineligible이다.
- `[CURRENT_REPO_FACT]` 0002 중간 DDL failure는 이 migration이 생성한 table만 역순 cleanup하고 Phase 1 row/revision과 pre-existing sentinel을 보존한다. raw final publish는 atomic no-replace이며 competing target을 overwrite하지 않는다.
- `[REPO_CONTRACT]` CP3-B 상태는 `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`이고 CP3-C는 `NOT STARTED`다.

## L. CP3-B/C/D checkpoint 분리

### CP3-B — Contract Foundation + Additive Migration + Raw/Source Trace

- 상태: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
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
- provider identity 기준 `ProviderPriceSnapshot`, nullable canonical linkage와 verified-only canonical current-price view
- Decimal/currency/timestamp-null/source trace/provider latest-state/idempotency/revision
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
| D-P08 | unknown provider symbol | response symbol not requested/provider-mapped | reject/quarantine | P0 | synthetic provider/canonical security creation zero |
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

### M.7 independent-review P1 regression acceptance

아래 일곱 case는 CP3-B/C/D 구현 시 삭제·완화할 수 없는 P0 acceptance다.

| ID | 목적 | 입력 | 기대 결과 | severity | false-green 방지 |
|---|---|---|---|---|---|
| IR-A | canonical mapping 없는 provider price | valid provider identity, `security_id=null`, `mapping_status=UNRESOLVED`, positive valid Toss price | `ProviderPriceSnapshot`과 provider latest 저장 가능; canonical current-price publish 0; issuer/company analysis link 0 | P0 | provider snapshot count 1과 canonical view/issuer link count 0을 동시에 assert |
| IR-B | verified mapping promotion의 ID 보존 | 기존 provider price history + 후속 approved canonical mapping | 기존 provider identity/price/source/hash/revision ID 유지; `security_id` linkage만 추가; historical rekey 0 | P0 | mapping 전후 모든 provider/history primary key와 hash set exact equality |
| IR-C | fake regulatory ID 방지와 provider storage 분리 | Toss symbol만 있고 corp_code/CIK 없음 | corp_code/CIK 생성 0; valid provider identity 기준 price 저장 가능 | P0 | regulatory column null/row count 0과 provider snapshot count 1을 함께 assert |
| IR-D | ISIN enrichment continuity | first `symbol=A, ISIN=null`; second `symbol=A, ISIN=valid` | 같은 `provider_security_identity_id`; identifier history 추가; new identity 0 | P0 | identity count/ID exact equality와 new ISIN history source link assert |
| IR-E | listDate enrichment continuity | first `symbol=A, listDate=null`; second same symbol + valid listDate | 같은 provider identity; listDate history 추가; anchor/rekey 0 | P0 | allocation anchor digest before/after exact equality와 identity count assert |
| IR-F | enrichment collision fail closed | existing identity A/B; 신규 ISIN evidence가 둘과 충돌 | auto merge 0; new identity 0; `UNRESOLVED_COLLISION`/`QUARANTINE`; 관련 latest 갱신 0 | P0 | merge/new/latest counts 0과 두 original identity/history 보존 assert |
| IR-G | enrichment 포함 deterministic rebuild | 동일 raw/source history를 clean DB에서 처음부터 replay | 최종 provider identity ID, immutable anchor와 identifier history가 원 실행과 동일 | P0 | 원 실행/rebuild의 ordered canonical dump와 hash set byte-for-byte compare; current clock 제외 |

### M.8 CP3-B independent-review hardening acceptance

| ID | 목적 | 입력 | 기대 결과 | severity | false-green 방지 |
|---|---|---|---|---|---|
| B-IR01 | later-fetch semantic idempotency | 같은 request/status/raw hash/contract와 later `fetched_at`·safe telemetry | first-seen raw/source 반환, source duplicate 0; dataset/parser/hash/revision 차이는 conflict | P0 | stored payload/row count와 각 conflict exception을 모두 assert |
| B-IR02 | exact trace graph | approved path와 mismatch dataset/raw/source/attempt/audit 조합 | mismatch persistence 0; `DAILY_FLOW` repository persistence 0; source+audit transaction rollback | P0 | source/audit before/after exact count와 path별 negative matrix |
| B-IR03 | VERIFIED relational integrity | missing/mismatched issuer/security, non-active identity, unrelated evidence | VERIFIED mapping 0; valid active lineage만 1 | P0 | rejected mapping 뒤 prior mapping ordered payload unchanged assert |
| B-IR04 | true SQL CAS/latest eligibility | 두 independent session이 같은 old hash로 다른 pointer write | 정확히 한 writer 성공, loser typed conflict, mixed row 0; timestamp-null CURRENT_PRICE latest 0 | P0 | barrier 기반 two-session execution, sequential 호출을 concurrency로 표시 금지 |
| B-IR05 | real mid-migration cleanup | 0001+fixture 뒤 0002 후반 table sentinel 충돌 | revision 0001, earlier CP3 table 0, Phase 1 rows/sentinel unchanged, retry 가능 | P0 | 첫 table failure가 아닌 후반 DDL failure와 byte/row dump compare |
| B-IR06 | raw no-replace race | publish 직전 competing same/different target | same bytes dedupe; different bytes typed conflict; overwrite 0; temp cleanup | P0 | in-memory hook으로 competing target을 먼저 만들고 surviving bytes assert |

## N. 비범위와 보안

CP3-C와 후속 live checkpoint의 별도 승인 전 계속 금지:

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
| ADR-011 nullable provider source time | `[REPO_CONTRACT]` `ACCEPTED 2026-08-25` | 기존 SourceRecord 유지; 별도 CP3-B authorization 전 구현 금지 |
| ADR-012 provider staging identity | `[REPO_CONTRACT]` `ACCEPTED 2026-08-25` | valid provider identity price만 provider scope에 허용; canonical Issuer/Security 자동 생성·canonical price publish 금지 |
| exact provider securityType enum mapping | `[LIVE_UNVERIFIED]` + independent evidence required | unknown 전부 quarantine |
| continuity-first provider ID | `[REPO_CONTRACT]` accepted ADR-012 | existing identity 우선 재사용; enrichment no-rekey; collision quarantine |
| canonical promotion authority/evidence | `[USER_DECISION_REQUIRED]` | staging UNRESOLVED 유지; name/symbol/ISIN-only promotion 금지 |
| exchange mapping | `[LIVE_UNVERIFIED]` | exchange 추정 금지, canonical promotion 금지 |
| timestamp-null current publication | `[REPO_CONTRACT]` accepted ADR-011 | DEGRADED/UNKNOWN, latest pointer 갱신 금지 |
| freshness thresholds | `[USER_DECISION_REQUIRED]` after minimal live evidence | 항상 UNKNOWN |
| SQLite provider current payload vs pointer | `[REPO_CONTRACT]` CP3-B minimum foundation implemented | `(dataset, provider_security_identity_id)` unique latest pointer만 구현; payload/history와 canonical projection은 CP3-D 전까지 금지 |

## checkpoint 판정

- CP1: `PASS`
- CP2: `COMPLETE`
- CP3-A: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-B: `REVISED AFTER INDEPENDENT REVIEW — AWAITING GPT RE-REVIEW`
- CP3-C: `NOT STARTED`
- Phase 2: `IMPLEMENTATION IN PROGRESS`

CP3-A는 application implementation 0, fixture/test/migration/dependency 변경 0, actual credential/API usage 0으로 closeout됐다. 별도 승인된 CP3-B는 provider contract/raw/source/migration/repository와 offline tests를 구현하고 첫 독립검증의 P1 5건/P2 1건을 보완했지만 re-review 전이므로 `PASS`, `APPROVED`, `COMPLETE`가 아니다. CP3-C는 `NOT STARTED`이고 automatic checkpoint progression은 `PROHIBITED`다. LIVE_UNVERIFIED 항목은 승인으로 승격되지 않는다.
