# Project Status

- 프로젝트 상태: `PHASE 2 IMPLEMENTATION IN PROGRESS — CP2 COMPLETE / CP3-A PASS — CONTRACT APPROVED AND CLOSED / CP3-B PASS — CLOSED / CP3-C1 PASS — CLOSED / CP3-C2-A PASS — CONTRACT APPROVED AND CLOSED / CP3-C2-B1 PLANNING — AWAITING GPT INDEPENDENT REVIEW / CP3-C2-B IMPLEMENTATION NOT STARTED / CP3-C2-C NOT STARTED / CP3-D NOT STARTED`
- 현재 Phase: `Phase 2 — CP3-C2-B1 issuer-authority runtime contract and additive migration design awaiting GPT independent review; CP3-C2-B implementation not started`
- 현재 버전: `0.1.0`
- Phase 1 최종 검증 commit: `57b2a63ead06d03191d8094e1689b8d2ab3d7764`
- Phase 1 PR: `#1`
- Phase 1 merge commit: `b1829a7375704271a21267e1fcf62808147be593`
- Release baseline tag: `v0.1.0`
- 최종 QA일: `2026-08-26 (CP3-C2-B1 documentation safety gates)`
- 실제 API 연결: `CP2-D2 one-shot PASS — OAuth + GET /api/v1/stocks만 검증`
- 실제 주문 기능: `비활성 / 비범위`
- OpenAI API 사용: `아니오`
- Phase 2 상태: `CP1 PASS / CP2 COMPLETE / CP3-A PASS — CONTRACT APPROVED AND CLOSED / CP3-B PASS — CLOSED / CP3-C1 PASS — CLOSED / CP3-C2-A PASS — CONTRACT APPROVED AND CLOSED / CP3-C2-B1 PLANNING — AWAITING GPT INDEPENDENT REVIEW / CP3-C2-B IMPLEMENTATION NOT STARTED / CP3-C2-C NOT STARTED / CP3-D NOT STARTED`
- CP3-B: `PASS — CLOSED`
- CP3-C1: `PASS — CLOSED`
- CP3-C2-A: `PASS — CONTRACT APPROVED AND CLOSED`
- ADR-013: `ACCEPTED`
- ADR-014: `PROPOSED — AWAITING GPT INDEPENDENT REVIEW`
- CP3-C2-B1: `PLANNING — AWAITING GPT INDEPENDENT REVIEW`
- CP3-C2-B implementation: `NOT STARTED`
- CP3-C2-C: `NOT STARTED`
- CP3-D: `NOT STARTED`
- Automatic checkpoint progression: `PROHIBITED`

## 완료 상태

- [x] Phase 1 상세 실행계획 승인
- [x] 합성 fixture 기반 FastAPI/SQLite Foundation
- [x] 읽기 전용 Company/Data Quality UI
- [x] OpenAPI 계약과 생성 타입 drift 검사
- [x] Windows setup 2회 재현
- [x] 개발 서버 smoke와 소유 프로세스 정리
- [x] backend 357개, frontend 43개, E2E 2개
- [x] migration 왕복과 fixture import 멱등성
- [x] production build, secret scan, Phase 1 policy scan
- [x] Phase 1 자체 QA 문서와 증빙 보존
- [x] 별도 Codex 작업의 독립 리뷰 PASS
- [x] 사용자 최종 승인과 PR #1 병합
- [x] Phase 1 완료 태그 `v0.1.0`
- [x] Phase 2 CP1 공식 계약 조사와 실행계획
- [x] Phase 2 CP2-A Toss-only connector namespace·dependency·credential config 경계
- [x] Phase 2 CP2-A origin/endpoint/import/account/order/secret negative canary
- [x] CP2-A 전체 회귀: backend 176개, frontend 43개, E2E 2개, build·secret·policy PASS
- [x] Phase 2 CP2-B strict OAuth response와 process-owned memory-only token manager
- [x] Phase 2 CP2-B 100-coroutine single-flight, monotonic expiry, generation-aware invalidation
- [x] Phase 2 CP2-B exact origin·method/path·header/query boundary와 401 1회 replay
- [x] CP2-B 전체 회귀: backend 251개, frontend 43개, E2E 2개, build·secret·policy PASS
- [x] Phase 2 CP2-B P2 hardening: public token manager/lease/raw bearer surface 제거, backend 252개
- [x] Phase 2 CP2-C client×group shared limiter와 7개 callable group exact mapping
- [x] Phase 2 CP2-C strict rate header telemetry, bounded 429/5xx retry와 safe typed exhaustion/deferred error
- [x] Phase 2 CP2-C concurrency·cancellation·401/OAuth 429 interaction offline 검증
- [x] CP2-C 독립 검토 P2 수정: 429 이후 Reset acquire wait와 backoff를 operation별 누적 30초 예산으로 통합
- [x] CP2-C P2 수정 전체 회귀: backend 321개, frontend 43개, E2E 2개, build·secret·policy PASS
- [x] CP2-D1 three-way opt-in, runtime contract drift gate, one-shot OAuth/stocks preflight tooling
- [x] CP2-D1 MockTransport·SelfTest·redaction 검증과 전체 회귀: backend 357개, frontend 43개, E2E 2개, build·secret·policy PASS
- [x] CP2-D2 actual OAuth와 `GET /api/v1/stocks` one-shot PASS, allowed-IP 실행 경로와 성공 응답 Limit/Remaining/Reset header 검증
- [x] Vitest stdout/stderr 분리, strict UTF-8 byte-safe JSON array와 한국어 test name을 포함한 exact 43 inventory gate
- [x] CP2 final integrated QA: P0 0 / P1 0 / unresolved functional P2 0 / deferred environment P2 1
- [x] CP3-A Security Master + Current Price 계획·계약 문서 작성
- [x] ADR-011 nullable source-time proposal 수정 및 ADR-012 provider staging identity proposal 추가
- [x] CP3-A application/test/fixture/migration/dependency/runtime/API route 변경 0
- [x] CP3-A 첫 GPT independent review: `CHANGES REQUIRED`, P0 0 / P1 2
- [x] P1-01 provider-scoped price/canonical view 분리 계약 보완
- [x] P1-02 continuity-first identity reconciliation과 enrichment acceptance 보완
- [x] CP3-A GPT independent re-review: `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0 / P1-01·P1-02 CLOSED
- [x] 사용자 ADR-011 및 revised ADR-012 승인
- [x] 사용자 CP3-A planning/contract 승인
- [x] 최종 9-file staged closeout regression과 P2 QA evidence gap 해소
- [x] CP3-B Contract Foundation + additive migration 별도 시작 승인
- [x] versioned provider source/identity contract와 nullable observation semantics
- [x] deterministic canonical request, exact-byte append-only raw store와 source revision
- [x] additive `0002_phase_02_cp3_foundation` 9-table metadata/pointer schema
- [x] SQLite insert-or-verify, atomic source/audit와 conditional latest pointer foundation
- [x] backend test inventory 357 → 448 증가와 targeted 100-test regression
- [x] CP3-B actual credential/Toss API request 0 및 CP3-C 미착수
- [x] CP3-B 첫 GPT independent review: P0 0 / P1 5 / P2 1
- [x] repeated-fetch idempotency, exact trace graph와 atomic source/audit hardening
- [x] VERIFIED mapping relational integrity, true SQL CAS와 latest eligibility hardening
- [x] real mid-migration rollback과 raw atomic no-replace race hardening
- [x] backend exact inventory 448 → 493 증가
- [x] structural audit P1-A: canonical request별 단일 linear source revision chain과 concurrent fork 차단
- [x] structural audit P1-B: VERIFIED mapping inclusive interval overlap 및 concurrent current promotion 차단
- [x] additive `0003_phase_02_cp3_b_invariants`와 backend exact inventory 493 → 509 증가
- [x] CP3-B GPT independent review: `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0
- [x] CP3-B documentation closeout와 `PASS — CLOSED`
- [x] CP3-C1 strict discovery/detail DTO, KR/US offline fixture와 conservative universe
- [x] CP3-C1 continuity-first identity allocation, enrichment no-rekey, collision quarantine와 lifecycle observation
- [x] CP3-C1 partial-detail exact audit와 `(fetched_at, source_version_id)` deterministic replay
- [x] additive `0004_phase_02_cp3_c1_security_master`와 backend exact inventory 509 → 540 증가
- [x] CP3-C1 GPT independent review: `CHANGES REQUIRED`, P0 0 / P1 2
- [x] P1-01 semantic current identifier resolution과 ambiguous-current fail-closed 보완
- [x] P1-02 complete detail batch duplicate-ISIN planning과 affected observation 전부 quarantine 보완
- [x] migration 0, backend exact inventory 540 → 544 증가
- [x] CP3-C1 GPT independent re-review: `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0 / P1-01·P1-02 CLOSED
- [x] CP3-C2-A KR/US canonical promotion authority 조사와 fail-closed 계약 작성
- [x] CP3-C2-A issuer/security 분리 matrix, 수동 승인 경계와 CP3-C2-B/C split 제안
- [x] CP3-C2-A GPT independent review: `CHANGES REQUIRED`, P0 0 / P1 2 / P2 1
- [x] P1-01 KRX listing market와 legal jurisdiction 분리 및 foreign issuer fail-closed 보완
- [x] P1-02 SEC registrant CIK와 accession/login/filing-agent CIK 권한 분리 보완
- [x] P2 24-hour freshness를 repository conservative approval policy로 명시
- [x] CP3-C2-A GPT independent re-review: `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0 / P1-01·P1-02·P2-01 CLOSED
- [x] 사용자 revised CP3-C2 authority contract와 ADR-013 명시적 승인
- [x] CP3-C2-A documentation closeout와 `PASS — CONTRACT APPROVED AND CLOSED`
- [x] CP3-C2-B1 design/contract checkpoint 별도 시작 승인
- [x] versioned AuthorityEvidence/Bundle/IssuerDecision/ApprovalEvent/IssuerAuthorityLink 설계
- [x] issuer-approved/security-unresolved와 additive `0005` migration proposal 설계
- [ ] CP3-C2-B1 GPT independent review와 사용자 계약 승인
- [ ] CP3-C2-B implementation 별도 시작 승인
- [ ] CP3-C2-C 별도 시작 승인
- [ ] CP3-D 별도 시작 승인

## Phase 1 종료 기준

```text
Phase 1: COMPLETE
Independent QA: PASS
PR: #1
Merge commit: b1829a7375704271a21267e1fcf62808147be593
Release baseline tag: v0.1.0
```

Phase 2 구현은 계속 진행 중이며 CP2만 `COMPLETE`다. CP2-A 보안 경계, CP2-B OAuth/token manager/exact HTTP client와 token-boundary hardening, CP2-C rate limiter/retry/error taxonomy와 cumulative-wait hardening, CP2-D1 safe preflight offline validation, CP2-D2 actual one-shot을 final integrated QA로 닫았다. 사용자 독립 실행의 safe fixed summary에서 provider contract drift 없음, OpenAPI `3.1.0`, provider version `1.2.14`, actual OAuth와 `GET /api/v1/stocks` 성공, allowed-IP 실행 경로와 성공 응답의 Limit/Remaining/Reset header 유효성을 확인했다. credential 값, token, body와 raw header 값은 기록하지 않았다.

CP3-A 첫 독립검증은 P1-01/P1-02를 발견했다. 보완 계약은 valid provider identity의 `ProviderPriceSnapshot`/latest를 nullable canonical linkage와 분리해 Phase 3/4 regulatory mapping 순환 의존을 제거하고, continuity-first 검색 → 단일 기존 ID 재사용 → identifier enrichment → collision quarantine → evidence 0일 때만 최초 anchor allocation 순서를 명시했다. GPT independent re-review와 사용자 승인으로 CP3-A는 `PASS — CONTRACT APPROVED AND CLOSED`다.

CP3-B는 기존 Phase 1 전역 `contract_version=0.1.0`, SourceRecord/Issuer/Security, fixture row/API/OpenAPI와 `0001`을 보존하면서 독립 provider source/identity 계약, canonical request, crash-safe raw store, immutable source revision, attempt/audit, identity/history/mapping/latest pointer foundation과 additive `0002`/`0003`을 구현하고 독립검증·문서 closeout을 거쳐 `PASS — CLOSED`다.

CP3-C1은 `/stocks/all` discovery와 `/stocks` detail의 strict offline DTO, 비식별 KR/US fixture, normalized semantic record/source observation/state event/detail-batch audit를 구현했다. 신규 identity는 같은 provider/market의 continuity evidence를 먼저 검색하고 증거가 0일 때만 valid ISIN → symbol+listDate → symbol+first-seen raw hash 순으로 immutable anchor를 발급한다. 후속 ISIN/listDate/symbol은 append-only history로 보강하며 rekey하지 않고, 다중·모순 증거는 auto merge/new identity/winner 없이 `UNRESOLVED_COLLISION`/`QUARANTINED`로 격리한다. 독립검토 P1 보완은 closed/open/SYMBOL_CHANGE 의미에 따른 current set으로 history ID/hash ordering 의존을 제거하고, 상충 current value를 fail closed하며, complete detail response의 duplicate ISIN affected observation 전부를 publish 전 collision plan으로 격리한다. provider가 주지 않은 symbol-change date는 만들지 않는다. discovery disappearance는 `DISCOVERY_MISSING`만 기록하고, inactive/delisted/partial/empty detail과 clean-DB deterministic replay를 감사 가능하게 보존한다. `0004`를 포함한 기존 migration은 변경하지 않았고 backend exact inventory는 544개다. GPT independent re-review는 `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0으로 P1-01·P1-02를 CLOSED 판정했으며 documentation closeout 뒤 CP3-C1은 `PASS — CLOSED`다.

CP3-C2-A는 2026-08-26 현재 OpenDART·KRX·대한민국 인터넷등기소·SEC EDGAR·Form 8-A/10-K/25·Nasdaq·NYSE·FINRA·CGS·GLEIF의 public authority scope와 licensing/availability 한계를 다시 조사해 canonical promotion 계약을 제안했다. GPT independent review는 KRX market이 KR legal jurisdiction을 증명하지 않는다는 P1-01과 EDGAR accession prefix/login CIK가 registrant CIK 권한이 아니라는 P1-02를 제기했다. 보완 계약은 KRX-listed foreign issuer의 관할권이 독립적으로 확인·표현되지 않으면 `UNRESOLVED / jurisdiction-contract-required`로 유지하고, SEC `registrant_cik`를 accepted evidence의 authoritative registrant metadata에서만 취하며 login/filing-agent CIK는 zero-authority audit provenance로 분리한다. 24시간 기준은 `REPO_POLICY / CONSERVATIVE_APPROVAL_FRESHNESS`로 명시했다. GPT independent re-review는 reviewed SHA `99bac1a7dc308414172e002496cd1e57f1c709c7`에 `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0, P1-01·P1-02·P2-01 CLOSED를 판정했고 사용자는 revised contract와 ADR-013을 명시적으로 승인했다. 따라서 CP3-C2-A는 `PASS — CONTRACT APPROVED AND CLOSED`, ADR-013은 `ACCEPTED`다. provider name/symbol/ticker, synthetic identifier, name-only/symbol-only merge와 arbitrary collision winner는 계속 승인 근거가 아니며 machine의 최대 positive state는 `READY_FOR_MANUAL_REVIEW`, 최종 issuer/security/VERIFIED linkage는 비모순 authority bundle에 대한 authenticated human approval이 필수다.

CP3-C2-B1은 accepted ADR-013을 변경하지 않고 issuer-authority runtime contract와 additive schema를 설계한다. 별도 version의 `AuthorityEvidence`, `AuthorityBundle`, `IssuerDecision`, `IssuerApprovalEvent`, `IssuerAuthorityLink`, deterministic semantic ID/hash, append-only correction/revocation/supersession, exact-bundle authenticated approval, global claim collision과 CAS head를 제안한다. issuer-only link는 `security_resolution_state=UNRESOLVED`를 강제하고 기존 `MappingStatus`를 확장하지 않는다. `0005_phase_02_cp3_c2_b_issuer_authority`는 proposal뿐이며 파일 생성·적용 0, 기존 `0001`~`0004`는 byte-identical이다. CP3-C2-B1은 `PLANNING — AWAITING GPT INDEPENDENT REVIEW`, ADR-014는 `PROPOSED`, CP3-C2-B implementation과 CP3-C2-C/CP3-D는 `NOT STARTED`다.

`[LIVE_VERIFIED]` 범위는 canonical provider contract, actual OAuth token issuance와 credential acceptance, allowed-IP 실행 경로, actual `GET /api/v1/stocks` 구조, 성공 응답의 Limit/Remaining/Reset header다. natural 429 `Retry-After`, actual 429/5xx, production retry timing, 나머지 Phase 2 market endpoint, CP3 이후 데이터 semantics/freshness는 계속 `[LIVE_UNVERIFIED]`다. Phase 2 전체 완료나 CP3 시작을 의미하지 않는다.

## 알려진 운영 조건

- Node.js 지원 범위는 24.16 이상 25 미만이며 QA 기준은 24.19.0이다.
- ADR-009는 아직 `PROPOSED`이며 독립 리뷰·승인 대상이다.
- 모든 표시 데이터는 합성 fixture이고 실제 투자 판단 자료가 아니다.
- Toss market connector는 CP2 범위에서 구현됐고 CP3-C1은 호출 없는 offline Security Master staging/reconciliation만 추가했다. CP3-C2-A는 approved authority contract와 documentation closeout만 작성했고 CP3-C2-B1은 runtime/schema design 문서만 추가했다. 실제 data collection/live API, canonical Issuer/Security promotion, authority migration, Current Price normalization/storage, scheduler와 화면 연결은 구현하지 않았다. CP3-C2-B1은 `PLANNING — AWAITING GPT INDEPENDENT REVIEW`, CP3-C2-B implementation과 CP3-C2-C/CP3-D는 `NOT STARTED`, automatic checkpoint progression은 `PROHIBITED`다. OpenDART/SEC/news/macro connector, 계좌와 주문도 구현하지 않았다.
- Windows 개발·QA 저장소는 현재 ASCII-only parent path를 사용한다. non-ASCII parent path의 setuptools editable build 실패는 `P2 DEFERRED / ENVIRONMENT CONSTRAINT`이며 CP2 business logic 결함으로 분류하지 않는다.
