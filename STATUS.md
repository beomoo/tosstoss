# Project Status

- 프로젝트 상태: `PHASE 2 IMPLEMENTATION IN PROGRESS — CP2 COMPLETE / CP3-A PASS — CONTRACT APPROVED AND CLOSED / CP3-B PASS — CLOSED / CP3-C1 PASS — CLOSED / CP3-C2-A PASS — CONTRACT APPROVED AND CLOSED / CP3-C2-B1 PASS — CONTRACT APPROVED AND CLOSED / CP3-C2-B IMPLEMENTATION IN PROGRESS / CP3-C2-B2-A PASS — CLOSED / CP3-C2-B2-B PASS — CLOSED / ADR-016 ACCEPTED / CP3-C2-B2-C 0006 IMPLEMENTATION IN PROGRESS / CP3-C2-B2-D NOT STARTED / CP3-C2-C NOT STARTED / CP3-D NOT STARTED`
- 현재 Phase: `Phase 2 — CP3-C2-B2-A PASS — CLOSED; CP3-C2-B2-B PASS — CLOSED; CP3-C2-B implementation IN PROGRESS; CP3-C2-B2-C 0006 schema implementation IN PROGRESS`
- 현재 버전: `0.1.0`
- Phase 1 최종 검증 commit: `57b2a63ead06d03191d8094e1689b8d2ab3d7764`
- Phase 1 PR: `#1`
- Phase 1 merge commit: `b1829a7375704271a21267e1fcf62808147be593`
- Release baseline tag: `v0.1.0`
- 최종 QA일: `2026-08-28 (ADR-016 acceptance recorded; 0006 implementation in progress)`
- 실제 API 연결: `CP2-D2 one-shot PASS — OAuth + GET /api/v1/stocks만 검증`
- 실제 주문 기능: `비활성 / 비범위`
- OpenAI API 사용: `아니오`
- Phase 2 상태: `CP1 PASS / CP2 COMPLETE / CP3-A PASS — CONTRACT APPROVED AND CLOSED / CP3-B PASS — CLOSED / CP3-C1 PASS — CLOSED / CP3-C2-A PASS — CONTRACT APPROVED AND CLOSED / CP3-C2-B1 PASS — CONTRACT APPROVED AND CLOSED / CP3-C2-B IMPLEMENTATION IN PROGRESS / CP3-C2-B2-A PASS — CLOSED / CP3-C2-B2-B PASS — CLOSED / ADR-016 ACCEPTED / CP3-C2-B2-C 0006 IMPLEMENTATION IN PROGRESS / CP3-C2-B2-D NOT STARTED / CP3-C2-C NOT STARTED / CP3-D NOT STARTED`
- CP3-B: `PASS — CLOSED`
- CP3-C1: `PASS — CLOSED`
- CP3-C2-A: `PASS — CONTRACT APPROVED AND CLOSED`
- ADR-013: `ACCEPTED`
- ADR-014: `ACCEPTED`
- ADR-015: `ACCEPTED` (`2026-08-28`)
- ADR-016: `ACCEPTED` (`2026-08-28`)
- CP3-C2-B1: `PASS — CONTRACT APPROVED AND CLOSED`
- CP3-C2-B implementation: `IN PROGRESS`
- CP3-C2-B2-A: `PASS — CLOSED`
- CP3-C2-B2-B: `PASS — CLOSED`
- CP3-C2-B2-C: `0006 SCHEMA IMPLEMENTATION IN PROGRESS`
- `0006`: `NOT CREATED / NOT IMPLEMENTED`
- B2-C WebAuthn/human-approval runtime: `NOT STARTED / NOT AUTHORIZED`
- CP3-C2-B2-D: `NOT STARTED`
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
- [x] CP3-C2-B1 GPT independent review: `CHANGES REQUIRED`, P0 0 / P1 4 / P2 1
- [x] P1-01 Windows Hello-backed WebAuthn trust root와 exact one-time approval challenge 보완
- [x] P1-02 KR court registry / US state registry legal-jurisdiction field-owner와 verified ingestion matrix 보완
- [x] P1-03 immutable AuthorityEvidenceApplication과 exact provenance/raw claim 보완
- [x] P1-04 production source-admission/fixture isolation과 exact acceptance matrix 보완
- [x] CP3-C2-B1 GPT independent re-review: `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0 / P1-01~P1-04 CLOSED / P2-01 non-blocking
- [x] 사용자 revised CP3-C2-B1 runtime contract와 ADR-014 documentation-closeout 승인
- [x] ADR-014 `ACCEPTED`와 CP3-C2-B1 `PASS — CONTRACT APPROVED AND CLOSED` closeout
- [x] B1 closeout commit 이후 CP3-C2-B implementation 별도 명시적 사용자 시작 승인
- [x] B2-A versioned authority source/evidence/application/bundle/claim/decision contract와 deterministic semantic ID/hash foundation
- [x] additive `0005_phase_02_cp3_c2_b_issuer_authority` 21-table schema, 40 append-only trigger, immutable insert-or-verify repository foundation
- [x] B2-A initial offline contract/repository/migration 54 tests와 backend exact inventory 598
- [x] B2-A GPT independent review: `CHANGES REQUIRED`, P0 0 / P1 3 / P2 1
- [x] P1-01 cross-bundle same-provider decision supersession / fork·graft rejection remediation
- [x] P1-02 B2-B positive engine 전 `READY_FOR_MANUAL_REVIEW` repository persistence fail-closed remediation
- [x] P1-03 immutable registration counter + append-only prior/asserted authentication counter history remediation
- [x] B2-A remediation targeted authority tests 69와 backend exact inventory 613
- [x] CP3-C2-B2-A GPT independent re-review: `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0 / P1-01~P1-03 CLOSED / P2-01 non-blocking
- [x] CP3-C2-B2-A documentation closeout와 `PASS — CLOSED`
- [x] CP3-C2-B2-B 별도 시작 승인
- [x] B2-B immutable exact production source-policy registry와 caller authority-escalation 차단
- [x] B2-B KR OpenDART/IROS 및 US SEC/exact-state-registry issuer bridge와 conservative freshness/current-head 평가
- [x] B2-B non-winner global collision scan, `BEGIN IMMEDIATE` transaction revalidation과 engine-only READY persistence
- [x] B2-B targeted 46, B2-A authority 69, backend exact inventory/full run 659
- [x] CP3-C2-B2-B GPT independent review: `CHANGES REQUIRED`, P0 0 / P1 5 / P2 1
- [x] P1-01 generic production admission fail-closed와 tests-only pre-admitted snapshot 분리
- [x] P1-02 caller evaluation time 제거와 engine-injected aware UTC server clock
- [x] P1-03 omitted current authority/provider state discovery와 co-current conflict fail-closed
- [x] P1-04 exact same deterministic canonical issuer non-collision / inconsistent subject conflict
- [x] P1-05 duplicate corp_code/CIK collision transaction의 impacted READY leaf 즉시 invalidation
- [x] B2-B remediation targeted 63, B2-A authority 69, backend exact inventory/full run 676
- [x] CP3-C2-B2-B GPT independent re-review of SHA `722a5036d7d05ad6b8de0314ff6ac5ee8dafacc2`: `CHANGES REQUIRED`, P0 0 / P1 2 new / P2 1; prior P1-01~P1-05 CLOSED 유지
- [x] P1-06 OpenDART/IROS 및 SEC/state-registry exact legal-name/history reconciliation gate
- [x] P1-07 accepted filing accession과 stable SEC issuer/entity bridge semantics 분리 및 deterministic former-symbol history
- [x] B2-B second remediation targeted 78, B2-A authority 69, backend exact inventory/full run 691
- [x] CP3-C2-B2-B second independent re-review of SHA `8093ee9389d4f7ae716482a87de5eae252e08eff`: `CHANGES REQUIRED`, P0 0 / P1 2 new / P2 1; P1-01~P1-07 CLOSED 유지
- [x] P1-08 official legal-name history의 exact KR `jurir_no` / exact US state-registry namespace·formation state·entity-number subject binding
- [x] P1-09 모든 relevant OpenDART/accepted SEC supporting legal name의 same-subject field-owner history reconciliation
- [x] B2-B third remediation targeted 89, B2-A authority 69, backend exact inventory/full run 702
- [x] CP3-C2-B2-B GPT independent re-review of SHA `d81148636c237ac8ab6b85e930d3926fae19c855`: `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0 / P2 1 non-blocking; P1-01~P1-09 CLOSED
- [x] CP3-C2-B2-B documentation closeout와 `PASS — CLOSED`
- [x] CP3-C2-B2-C 별도 시작 승인과 implementation-entry schema audit
- [x] SG-01 first-enrollment bootstrap relational gap 확인
- [x] SG-02 credential-management reauthentication/counter relational gap 확인
- [x] ADR-015 및 additive future-`0006` schema-remediation proposal 작성
- [x] GPT independent review of SHA `fd0535fdd022f0171a63a83cb2861e924a92da64`: `CHANGES REQUIRED`, P0 0 / P1 2 / P2 1 non-blocking; SG-01/SG-02와 additive Option A 원칙 수용
- [x] P1-SR-01 authenticated final-active-credential revoke와 exact empty active state 정정
- [x] P1-SR-02 exact `reviewer-credential-state/0.1.0`, server-computed hash boundary와 lifecycle-event/outcome deferred binding 정정
- [x] GPT independent re-review of SHA `e016fc59973e5c81181e7cf20c1ebe3d7aada043`: `CHANGES REQUIRED`, P0 0 / P1 1 / P2 1 non-blocking; P1-SR-01/P1-SR-02 CLOSED
- [x] P1-SR-03 every terminal failure의 challenge consumption + unchanged-state operation outcome atomic terminalization, closed result mapping, no-orphan issuance/continuation 계약 정정
- [x] GPT independent review of SHA `f73115ea1182e27259787460307a01b4c3874312`: `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0 / P2 1 non-blocking; SG-01/SG-02/P1-SR-01/P1-SR-02/P1-SR-03 CLOSED
- [x] 사용자 explicit ADR-015 acceptance (`2026-08-28`)와 schema architecture approval 기록
- [x] Separate `0006` implementation attempt의 fail-closed stop: IG-01/IG-02 확인, changed files 0, `0006` 0
- [x] ADR-016 exact authorization enum/matrix, exact 8-column child FK와 hash-preimage amendment 제안
- [x] ADR-016 GPT independent review P0 0 / P1 0 및 explicit user acceptance (`2026-08-28`)
- [ ] Approved `0006` schema implementation과 independent review
- [ ] CP3-C2-B2-D 별도 시작 승인
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

CP3-C2-B1은 accepted ADR-013을 변경하지 않고 issuer-authority runtime contract와 additive schema를 설계한다. 첫 GPT independent review는 P0 0 / P1 4 / P2 1로 authenticated-human trust root, exact legal-jurisdiction field owner, ADR-013 provenance minimum과 production source-admission/acceptance isolation의 보완을 요구했다. Revised contract는 exact `localhost` RP/origin의 Windows Hello-backed WebAuthn, fresh five-minute one-time decision/bundle/hash/disposition-bound assertion, KR Supreme Court/Internet Registry와 relevant US formation-state registry의 decisive jurisdiction authority, immutable `AuthorityEvidenceApplication`, exact raw claim/source locator/document reference, immutable `AuthoritySourcePolicy`와 permanent fixture/test taint를 추가했다. Bundle은 bare evidence가 아니라 exact candidate application을 참조하고, expanded matrix는 scenario별 Issuer/Security/VERIFIED/rekey count와 human disposition 가능 여부를 고정한다. issuer-only link는 `security_resolution_state=UNRESOLVED`를 강제하고 기존 `MappingStatus`를 확장하지 않는다. GPT independent re-review는 SHA `f3a7a3c4cc99de9cd9656544c1b29e3d03df6911`에 `PASS WITH CLOSEOUT CONDITION`, P0 0 / P1 0을 판정해 P1-01~P1-04를 모두 `CLOSED` 처리했다. P2-01 GitHub CI execution evidence 부재는 non-blocking이며 local safety-gate 결과는 GitHub CI evidence가 아니다. 사용자는 revised contract와 ADR-014를 documentation closeout 범위로 명시적으로 승인했다. 따라서 ADR-014는 `ACCEPTED`, CP3-C2-B1은 `PASS — CONTRACT APPROVED AND CLOSED`다. B1 closeout 당시 `0005_phase_02_cp3_c2_b_issuer_authority`는 proposal뿐이고 파일 생성·적용 0, 기존 `0001`~`0004`는 byte-identical이었으며 CP3-C2-B implementation도 별도 시작 승인 전이었다.

별도 사용자 승인으로 CP3-C2-B implementation에 진입했고 B2-A foundation은 독립 재검토와 closeout 뒤 `PASS — CLOSED`다. B2-A는 canonical UTF-8/NFC JSON과 SHA-256 기반 versioned authority ledger, permanent fixture/test taint, exact candidate/application membership, non-winner identifier collision 보존, additive 21-table `0005`와 append-only storage를 제공한다. 별도 B2-B 시작 승인에 따라 immutable server-owned exact source registry, KR OpenDART corp-code/overview ↔ verified IROS exact `jurir_no` ↔ CP3-C1 symbol bridge, US accepted SEC registrant/filer metadata ↔ individually admitted Delaware domestic-formation registry ↔ CP3-C1 non-name bridge를 구현했다. 첫 independent review의 P1-01~P1-05 remediation은 generic production admission fail-closed, tests-only pre-admitted snapshot, engine-owned UTC clock, complete current-state discovery, same canonical subject semantics와 impacted READY invalidation을 추가했고 독립 재검토에서 모두 `CLOSED`로 확인됐다. SHA `722a5036d7d05ad6b8de0314ff6ac5ee8dafacc2` 재검토는 P0 0 / P1 2 new / P2 1을 판정했다. Second remediation은 KR OpenDART/IROS와 US accepted SEC/state-registry의 `LEGAL_NAME` scope를 positive bundle에 필수로 추가하고, exact NFC name 또는 field-owning registry의 immutable linear correction/supersession history만 허용한다. Provider name/ticker는 name conflict를 고칠 수 없다. Multiple accepted SEC filings는 각 filing의 exact same-document CIK/role/bridge/name provenance를 독립 검증하되 accession 자체를 stable issuer/entity conflict key로 사용하지 않는다. Formation state/entity number가 같으면 coexist할 수 있고, incompatible entity facts는 conflict이며 former provider symbol은 authority acceptance chronology가 current provider bridge를 deterministic하게 설명할 때만 허용한다. Historical filing age는 latest-status freshness와 분리된다. Generic READY는 계속 `REVIEW_READY_ENGINE_NOT_IMPLEMENTED`로 거부되며 machine output은 `UNRESOLVED`, `READY_FOR_MANUAL_REVIEW`, `STALE`, `REVIEW_REQUIRED`뿐이다. Second-remediation local self-QA는 targeted `78`, B2-A authority `69`, backend `691`, frontend `43`, E2E `2`를 통과했으며 external authority/provider request와 credential use는 0이다. B2-B는 `REMEDIATED — AWAITING GPT INDEPENDENT RE-REVIEW`; B2-C/B2-D와 CP3-C2-C/CP3-D는 `NOT STARTED`, automatic progression은 `PROHIBITED`다.

SHA `8093ee9389d4f7ae716482a87de5eae252e08eff`의 second independent re-review는 P1-01~P1-07을 `CLOSED`로 확인하고 P1-08/P1-09를 새로 제기했다. Third remediation은 official decisive legal-name history의 모든 component를 KR IROS exact `corporate_registration_reference`/`jurir_no` 또는 US exact state-registry namespace·formation state·`state_entity_number` companion evidence에 독립적으로 bind한다. Relation edge, source namespace, name, role, insertion order 또는 provider name/symbol만으로 subject sameness를 인정하지 않는다. 모든 relevant OpenDART/accepted SEC supporting legal name은 exact current decisive name이거나 동일 field-owner legal entity의 immutable `CORRECTS`/`SUPERSEDES` history에 포함돼야 하며, 설명되지 않은 이름 하나 또는 cross-entity history가 있으면 conflict다. Provider name/ticker, fuzzy/case/punctuation/suffix/whitespace normalization은 계속 zero authority이고 historical filing age는 latest-status freshness와 분리된다. Third-remediation LOCAL self-QA는 targeted `89`, B2-A authority `69`, backend `702`, frontend `43`, E2E `2`를 통과했다. Migrations `0001`~`0005`, generic production admission/READY fail-closed, `BEGIN IMMEDIATE`, 모든 zero counter와 later-checkpoint 금지는 유지된다.

GPT independent review of SHA `d81148636c237ac8ab6b85e930d3926fae19c855` returned `PASS WITH CLOSEOUT CONDITION`, P0 `0`, P1 `0`, P2 `1` non-blocking, and closed P1-01 through P1-09. CP3-C2-B2-B is therefore `PASS — CLOSED`. Production authority admission and generic READY remain fail closed; the machine maximum positive state remains `READY_FOR_MANUAL_REVIEW`; the engine-owned UTC clock, complete current-state discovery, exact KR/US issuer bridge, same-subject legal-name history, all-supporting-name reconciliation, collision handling and impacted-READY invalidation remain active. This documentation closeout changes no implementation and does not authorize B2-C. CP3-C2-B implementation remains `IN PROGRESS`; B2-C/B2-D, CP3-C2-C and CP3-D remain `NOT STARTED`; automatic progression remains `PROHIBITED`.

사용자는 이후 CP3-C2-B2-C 시작을 명시 승인했지만, starting SHA
`60f2805d2390c91a026b3381877006be9000dedb`의 accepted B1 contract와 frozen
`0005`를 implementation-entry 단계에서 재대조한 결과 runtime 구현 전에 두
schema blocker가 확인됐다. SG-01은 유효한 credential이 존재하기 전
server-created Windows-owner-SID-bound first-enrollment bootstrap, WebAuthn
create challenge, finite expiry와 실패 포함 unique terminal consumption을
관계형으로 보존할 table/FK가 없다는 점이다. SG-02는 existing
`reviewer_authentication_events`가 issuer decision/bundle/disposition에 필수
결합되어 active credential의 `ADD_CREDENTIAL`/`REPLACE_CREDENTIAL` fresh
assertion과 counter advancement를 정직하게 기록할 수 없다는 점이다.
`payload_json`, process/browser memory, fake issuer challenge 또는 synthetic
credential은 허용되지 않는다. 2차 검증은 issuer `SUPERSEDED`를 blocker에서
제외했다. 당시 ADR-015 revision은 existing table rebuild 없이 six append-only
credential-operation ledger tables와 exact additive indexes/guards를 제안했다.
`0001`–`0005` 변경과 `0006` 생성/적용, runtime/test/
frontend/dependency 변경, real credential/approval/canonical/link/live request는
모두 `0`이었다.

GPT independent review of the first schema proposal at SHA
`fd0535fdd022f0171a63a83cb2861e924a92da64` returned `CHANGES REQUIRED`, P0
`0`, P1 `2`, P2 `1` non-blocking. SG-01/SG-02 and additive Option A were
accepted in principle. P1-SR-01 is remediated by allowing the currently active
credential to authenticate its own final revocation and recording the exact
empty active set; afterward issuer approval/add/replace/further revoke fail
closed, first enrollment cannot restart and recovery/reset remains absent.
P1-SR-02 is remediated by the exact versioned
`reviewer-credential-state/0.1.0` canonical preimage, server-side SHA-256
recomputation under `BEGIN IMMEDIATE`, relational SQLite enforcement without an
undeclared SHA UDF, and a mandatory deferred lifecycle-authorization-to-
successful-outcome binding. GPT independent re-review of SHA
`e016fc59973e5c81181e7cf20c1ebe3d7aada043` verified P1-SR-01 and P1-SR-02
`CLOSED` and returned one new P1-SR-03. The final revision makes every failed or
expired terminal challenge consumption mutually deferred-bound to exactly one
unchanged-state operation outcome before a typed result is returned. Operation
and initial challenge are issued atomically; the sole nonterminal add/replace
assertion success commits its verified counter event and one five-minute
registration challenge in the same writer transaction. Failed registration
preserves that counter event, appends no lifecycle transition and terminalizes
the operation. At that revision ADR-015 stayed `PROPOSED` and P1-SR-03 awaited
GPT independent re-review.

GPT independently reviewed the resulting SHA
`f73115ea1182e27259787460307a01b4c3874312` as `PASS WITH CLOSEOUT CONDITION`,
P0 `0`, P1 `0`, P2 `1` non-blocking, and closed SG-01, SG-02, P1-SR-01,
P1-SR-02 and P1-SR-03. The user explicitly accepted ADR-015 on `2026-08-28`,
so the schema architecture is approved. A separately authorized implementation
attempt then stopped fail closed with no file changes and no `0006` after
discovering GPT-confirmed IG-01 (incomplete `authorization_kind` matrix) and
IG-02 (missing child trust columns for the exact eight-column operation FK).
ADR-016 defines only the exact four-token/five-row matrix, the three copied
server-owned trust columns in both child tables, exact eight-column FKs and
corresponding hash-preimage coverage. GPT independent review of SHA
`4104973d84307b80a236d9b737b2d29339b27153` returned P0 `0` / P1 `0`; the user
explicitly accepted ADR-016 on `2026-08-28` and separately authorized only the
approved `0006` schema implementation. CP3-C2-B2-C `0006` implementation is
`IN PROGRESS`; it is not PASS/CLOSED and B2-C runtime is
`NOT STARTED / NOT AUTHORIZED`. B2-D, CP3-C2-C and CP3-D remain `NOT STARTED`;
automatic progression is `PROHIBITED`. GitHub CI execution evidence remains
absent/non-blocking; LOCAL checks are not GitHub CI evidence.

`[LIVE_VERIFIED]` 범위는 canonical provider contract, actual OAuth token issuance와 credential acceptance, allowed-IP 실행 경로, actual `GET /api/v1/stocks` 구조, 성공 응답의 Limit/Remaining/Reset header다. natural 429 `Retry-After`, actual 429/5xx, production retry timing, 나머지 Phase 2 market endpoint, CP3 이후 데이터 semantics/freshness는 계속 `[LIVE_UNVERIFIED]`다. Phase 2 전체 완료나 CP3 시작을 의미하지 않는다.

## 알려진 운영 조건

- Node.js 지원 범위는 24.16 이상 25 미만이며 QA 기준은 24.19.0이다.
- ADR-009는 아직 `PROPOSED`이며 독립 리뷰·승인 대상이다.
- 모든 표시 데이터는 합성 fixture이고 실제 투자 판단 자료가 아니다.
- Toss market connector는 CP2 범위에서 구현됐고 CP3-C1은 호출 없는 offline Security Master staging/reconciliation만 추가했다. CP3-C2-A와 B1은 approved authority/runtime-schema contract를 확정했고, B2-A는 immutable authority ledger와 additive `0005` foundation, B2-B는 trusted pre-admitted immutable evidence만 평가하는 offline bridge/collision/freshness machine engine을 구현했다. 신규 production evidence operational admission은 fail closed이며 live ingestion은 구현하지 않았다. Reviewer/WebAuthn/approval/link table은 존재하지만 WebAuthn runtime, approval route/execution, canonical Issuer/Security promotion, VERIFIED mapping, Current Price normalization/storage, scheduler와 화면 연결은 구현하지 않았다. CP3-C2-B2-A와 B2-B는 `PASS — CLOSED`; ADR-016은 `ACCEPTED`; B2-C `0006` schema implementation은 `IN PROGRESS`이고 runtime은 `NOT STARTED / NOT AUTHORIZED`; B2-D와 CP3-C2-C/CP3-D는 `NOT STARTED`, automatic checkpoint progression은 `PROHIBITED`다. OpenDART/SEC/IROS/US state registry/news/macro live connector, 계좌와 주문도 구현하지 않았다.
- Windows 개발·QA 저장소는 현재 ASCII-only parent path를 사용한다. non-ASCII parent path의 setuptools editable build 실패는 `P2 DEFERRED / ENVIRONMENT CONSTRAINT`이며 CP2 business logic 결함으로 분류하지 않는다.
