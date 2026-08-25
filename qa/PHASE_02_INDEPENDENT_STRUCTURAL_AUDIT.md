# Phase 2 Independent Structural Audit

## Audit metadata

- Repository: `beomoo/tosstoss`
- Branch: `feature/phase-02-toss`
- Audited HEAD: `a33cf6e0ff74bf7db1a373061f90785a92709696`
- Audit mode: independent, read-only
- Actual Toss API requests: `0`
- Credentials used: `0`
- Audit-time repository changes: `0`
- Audit-time commits: `0`
- Audit-time pushes: `0`

> 이 문서는 read-only 감사가 완료된 뒤, 사용자 요청에 따라 2차 GPT 검증용으로 별도 생성한 보고서다. 따라서 위 `Audit-time repository changes: 0`은 감사 수행 당시의 상태를 뜻하며, 이 보고서 파일 생성 자체는 후속 문서화 변경이다.

## 1. Executive conclusion

독립 판정은 **B**다.

CP2에는 구현 중 실제 결함이 있었지만 `94488f7c`의 token surface hardening과 `fe650760`의 cumulative retry-budget 수정으로 closeout 전에 해결됐다. 현재 blocking work는 CP3-B에 있다.

- CP2 재오픈: **NO**
- CP3-A: **PASS**
- CP3-B: **CHANGES REQUIRED — P1 2건**
- CP3-C 시작: **NO**
- 감사 대상 HEAD: `a33cf6e0ff74bf7db1a373061f90785a92709696`
- 감사 종료 시 working tree/index 변경: `0/0`

## 2. Current blocking findings

### P1-01 — 다른 raw 응답의 source revision link를 저장소가 강제하지 않음

계약 B-S04는 동일 request에 다른 raw bytes가 들어오면 `two source versions + link`를 요구한다.

근거:

- `plans/PHASE_02_CP3_A_CONTRACT.md:529`
- `services/api/src/toss_dashboard_api/repositories/provider.py:398`
- `tests/backend/test_provider_repository.py:515`

현재 repository는:

- 동일 raw hash만 duplicate로 처리하고,
- `supersedes_id`가 제공된 경우에만 parent를 검사하며,
- 동일 canonical request의 두 번째 서로 다른 raw를 또 다른 `ORIGINAL`로 저장하는 것을 막지 않는다.
- 현재 positive test도 caller가 올바른 `AMENDED + supersedes_id`를 제공하는 경우만 검증한다.

따라서 multiple roots와 revision fork가 생길 수 있어 deterministic rebuild와 revision provenance를 훼손한다.

- Severity: **P1**
- Recommended fix: 첫 version 이후에는 repository transaction에서 현재 chain leaf를 확인하고, 다른 raw는 non-`ORIGINAL`이면서 정확한 leaf를 supersede하도록 강제한다. 두 번째 `ORIGINAL`, fork, 이미 superseded된 parent를 거부하는 negative/concurrency tests를 추가한다.

### P1-02 — 상충하는 동시 유효 VERIFIED mapping을 허용함

원래 CP3-B P1-03의 행 단위 관계 검증은 수정됐다. VERIFIED mapping은 active identity, 실제 issuer/security 관계, identity lineage evidence를 요구한다.

근거:

- `services/api/src/toss_dashboard_api/repositories/provider.py:279`
- `services/api/src/toss_dashboard_api/repositories/provider.py:607`
- `services/api/alembic/versions/0002_phase_02_cp3_foundation.py:190`

그러나 현재 schema/repository에는 동일 provider identity에 대해 서로 다른 canonical security를 가리키는 두 개의 open-ended VERIFIED mapping을 차단하는 조건이 없다.

- migration에는 mapping ID PK와 행 내부 CHECK만 있다.
- `record_identity_mapping()`은 기존 유효 mapping과의 중복, 기간 겹침, canonical target 충돌을 조회하지 않는다.
- 이 상태는 verified-only canonical projection의 결과를 모호하게 만든다.

아직 canonical price projection이 구현되지 않았으므로 P0까지는 아니지만 CP3-C가 신뢰할 수 없는 foundation이다.

- Severity: **P1**
- Recommended fix: identity당 특정 시점에 하나의 VERIFIED target만 유효하도록 transactional invariant를 정의한다. overlapping/open-ended conflict를 fail closed하고 concurrent promotion 및 historical interval 전환 negative tests를 추가한다.

### Non-blocking P2

1. latest pointer 외 여러 insert-or-verify 경로는 `SELECT → INSERT` 방식이라 미래 동시 수집에서 raw `IntegrityError`가 노출될 수 있다. 아직 collection job이 없어 현재 workflow blocker는 아니며 **P2 concurrency hardening**이다.
2. raw no-replace는 hard-link primitive가 지원되지 않으면 안전하게 실패한다. 데이터 손상은 없지만 filesystem portability는 **P2**다.

## 3. Git history reconstruction

살아 있는 Git 이력은 `e2c0db5e`부터 감사 대상 HEAD까지 완전한 single-parent 선형이다. merge commit이나 병렬 side branch 흔적은 없다. 과거 force-rebase가 한 번도 없었다는 사실까지 Git만으로 증명할 수는 없지만, 현재 graph에는 unexpected merge/rebase 결과가 없다.

| 단계 | Commit | 실제 변경 범위 |
|---|---|---|
| Phase 2 start | `e2c0db5e` | Phase 2 plan, decisions, known issues |
| CP2-A | `e1bca561` | env/config/logging/dependency policy, Toss namespace, security tests |
| CP2-A validation | `aa779cac` | 문서 |
| CP2-B | `6a823edc` | auth/client/errors/models 및 auth/client tests |
| CP2-B hardening | `94488f7c` | public token access 제거, auth/client/tests/policy |
| CP2-C | `e0017a18` | rate limiter/retry/error taxonomy 및 tests |
| CP2-C hardening | `fe650760` | Reset wait를 cumulative 30-second budget에 포함 |
| CP2-D1 | `65edc185` | preflight wrapper/runner/helper/tests |
| CP2-D1 fixes | `472104de`, `8b046799`, `7840eee` | secret-scan, formatting, policy digest |
| CP2-D1 docs | `4664a01` | 문서 |
| Vitest/inventory | `411749e1` | `test.ps1`, policy scan만 변경 |
| CP2 closeout | `6bd5d2ae` | STATUS/DECISIONS/KNOWN_ISSUES/CHANGELOG/PROGRESS만 변경 |
| CP3-A start | `3e09ba41` | documentation-only contract |
| CP3-A report | `386a0b2f` | documentation-only |
| CP3-A fixes | `6a3e1c21` | contract/docs/QA |
| CP3-A closeout | `c210c1af` | contract/docs/QA |
| CP3-B implementation | `58cc17d8` | provider contracts/raw/repository/0002 migration/tests |
| CP3-B fix/current audited HEAD | `a33cf6e0` | 여섯 finding hardening 및 tests/docs |

CP2 closeout 이후 Toss auth/client/rate/preflight/config/logging/dependencies는 변경되지 않았다. 공유 `scripts/policy-scan.ps1`과 `scripts/test.ps1`만 CP3-B test inventory와 digest를 추가하도록 변경됐고, 기존 Toss 금지 규칙의 삭제·완화는 확인되지 않았다.

## 4. CP2 re-audit

| 범위 | 독립 판정 | 분류 |
|---|---|---|
| CP2-A dependency/config | `httpx==0.28.1`, server-only `SecretStr`, safe defaults 유지 | NOT A DEFECT |
| Exact origin | `https://openapi.tossinvest.com`, HTTPS/host/port/userinfo 경계 고정 | NOT A DEFECT |
| Forbidden surfaces | account/order/conditional-order/WebSocket callable surface 없음; policy canary 유지 | NOT A DEFECT |
| Account header | runtime `X-Tossinvest-Account` 없음 | NOT A DEFECT |
| Secret/log boundary | structured allowlist logging 및 recursive redaction 적용 | NOT A DEFECT |
| CP2-B OAuth | exact client-credentials form, strict response validation | NOT A DEFECT |
| Token lifecycle | memory-only, async single-flight, monotonic expiry, generation-aware invalidation | NOT A DEFECT |
| 401 replay | `expired-token`/`invalid-token`에만 최대 1회 | NOT A DEFECT |
| Public token surface | 구현 중 존재했던 surface가 `94488f7c`에서 제거됨 | CLOSED |
| HTTP transport | redirect off, TLS verify on, `trust_env=false` | NOT A DEFECT |
| CP2-C mapping | OAuth 포함 12 method/path가 7 exact rate groups에 매핑됨 | NOT A DEFECT |
| Retry eligibility | exact 429 codes와 `500/502/503/504 + approved code`만 retry | NOT A DEFECT |
| Transport errors | 자동 retry하지 않음 | NOT A DEFECT |
| Retry timing | Retry-After 우선, Reset 연동, 총 retry-related sleep 30초, 최대 3 attempts | NOT A DEFECT |
| Concurrency/cancellation | group lock 및 cancellation-safe context 사용 | NOT A DEFECT |
| CP2-D gates | `-Live`, `-ConfirmReadOnly`, exact `READ_ONLY_ONE_SHOT` | NOT A DEFECT |
| Credential/drift | contract drift 검사 후 env-only credentials 접근 | NOT A DEFECT |
| One-shot/output | OAuth 1회 + stocks 1회, fixed safe summary, body/token/raw header 저장 surface 없음 | NOT A DEFECT |
| Natural provider behavior | natural 429, actual 429/5xx, 다른 market endpoint와 production timing | LIVE_UNVERIFIED |
| Windows non-ASCII editable install | runtime 기능과 무관한 portability 제약 | P2, DEFERRED |

계획 자체도 credential preflight가 미실행이어도 명시적 `LIVE_UNVERIFIED`로 CP2를 닫을 수 있게 규정한다.

근거: `plans/PHASE_02_EXECUTION_PLAN.md:491`

따라서 남은 live 항목은 CP2 acceptance 실패가 아니다.

## 5. CP2 closeout validity

`6bd5d2ae9c26f02f2cd4bd75a474633a9082fa16`은 코드 수정 없이 문서만 변경했다. 그 parent인 `411749e171a717b3060973cb7b127fb94f592bab` 시점에는 token surface와 retry-budget 결함이 이미 수정돼 있었다.

증거 분류:

- **Repository에서 직접 검증 가능:** 현재 구현 구조, test assertions, exact endpoint/group 표, policy canaries, 선형 Git 이력, CP2 runtime files가 closeout 이후 byte-level 미변경이라는 사실.
- **Codex/local claims:** backend 357/357, frontend 43/43, E2E 2/2, migration/build/secret/policy exit 0. Markdown 보고는 있으나 원시 실행 로그는 closeout commit에 보존되지 않았다.
- **User live-test claims:** 실제 OAuth, allowed IP, `/stocks`, 성공 rate headers, drift 없음. 이는 문서화된 사용자 보고이며 이번 감사에서 재실행하지 않았다.
- **독립적으로 재현 불가능한 주장:** 당시 실제 응답 version/header 값과 live 실행 중 token/body가 어디에도 유출되지 않았다는 역사적 사실, 당시 full-suite exact exit code. 현재 코드가 그러한 유출을 하지 않도록 설계된 것은 직접 확인된다.

결론적으로 closeout의 증거 보존 품질에는 개선 여지가 있지만, acceptance 기준과 현재 코드 상태를 기준으로 `CP2 COMPLETE / P0 0 / P1 0 / unresolved functional P2 0` 판정은 정당했다.

**Should CP2 be reopened NOW? NO.**

## 6. Post-CP2 regression

`6bd5d2ae..a33cf6e`에서 다음은 변경 0이다.

- Toss auth/client/rate limiter/preflight
- config와 logging/redaction
- `.env.example`
- dependency/lock
- live preflight scripts

변경된 보안 관련 shared files는 `scripts/policy-scan.ps1`, `scripts/test.ps1`뿐이다. CP3-B test file allowlist, inventory 357→493, control digest를 추가했으며 Toss security pattern을 완화한 변경은 확인되지 않았다.

**CP2 runtime/security boundary at audited HEAD: CHANGED-SAFE**

정확히는 runtime은 `UNCHANGED`, shared QA/security control-plane만 `CHANGED-SAFE`다.

## 7. CP3-A audit

- CP2 closeout 다음 commit에서 documentation-only로 시작했으므로 구조상 시작 가능했다.
- 최초 P1 두 건은 실제였다.
  - canonical mapping을 price storage의 선행조건으로 둔 순환 의존
  - identifier enrichment 전에 continuity search가 없었던 ID 재발급 위험
- 수정 계약은 provider-scoped price와 canonical projection을 분리하고, continuity-first → existing ID reuse → enrichment/no-rekey → collision quarantine을 명시한다.
- 수정 과정과 closeout 모두 documentation-only였고 CP3 implementation을 선행하지 않았다.
- exact enum/exchange/freshness/promotion authority는 fail-closed 상태로 명시적으로 후속 checkpoint에 남았다.

**CP3-A verdict: PASS**

## 8. CP3-B original findings re-evaluation

| Finding | 판정 | 근거 |
|---|---|---|
| P1-01 repeated-fetch idempotency | CLOSED | later `fetched_at`/safe telemetry 제외, semantic conflict fail closed |
| P1-02 trace graph | CLOSED | exact path→dataset, request→raw→source→attempt/audit, atomic source+audit |
| P1-03 verified mapping integrity | CLOSED | 원 finding의 relational integrity는 구현됨; 단, 별도의 active mapping conflict P1이 새로 확인됨 |
| P1-04 SQL CAS/latest eligibility | CLOSED | one-statement conditional UPDATE, first-insert conflict handling, two-session barrier test |
| P1-05 migration mid-failure | CLOSED | late sentinel failure 후 created tables만 제거, 0001/fixture/sentinel 보존 및 retry test |
| P2 raw no-replace race | CLOSED | atomic hard-link create, same-byte dedupe, different-byte conflict, temp cleanup |

CP3-C identity reconciliation, CP3-D price payload/ordering, 실제 enum·freshness semantics가 없는 것은 현재 CP3-B defect가 아니다. 명시적으로 후속 범위다.

## 9. Workflow and process audit

| 항목 | 판정 |
|---|---|
| Remote Codex prompt 반복/recovery case D | QA/process 문제. 최종 Git에는 fast-forward fix 하나만 남아 code duplication은 없음 |
| Stale expected SHA | QA/process 문제. mismatch 시 재실행보다 prompt를 폐기·재생성해야 함 |
| 다수 QA report variants | process noise. self-report와 independent verdict가 혼재해 authority가 불명확함 |
| STATUS/PROGRESS/CHANGELOG/QA 상태 중복 | QA/process 문제이자 drift 위험 |
| 승인 contract의 구현 후 반복 수정 | process 문제. contract와 implementation record를 분리해야 함 |
| Policy digest maintenance | 유용한 security control이지만 brittle한 QA maintenance; runtime code problem은 아님 |
| Automatic checkpoint progression | 현재 규칙은 올바름. CP3-C가 시작되지 않았으므로 위반 없음 |

간소화 권고:

1. `STATUS.md`만 현재 상태의 canonical authority로 사용한다.
2. 승인 contract는 immutable하게 두고 변경은 새 ADR/amendment로 남긴다.
3. checkpoint마다 self-QA 1개, independent QA 1개, 필요 시 fix/re-review 1개만 유지한다.
4. prompt의 exact SHA는 실행 직전 생성하고 mismatch면 즉시 중단한다.
5. policy digest는 최종 staged bytes에서 한 번만 생성·검토한다.
6. 다음 checkpoint 승인에는 승인 대상 commit SHA를 명시한다.

## 10. Canonical current state

| 단계 | 상태 | P0 | P1 | P2 | LIVE_UNVERIFIED | 다음 checkpoint |
|---|---|---:|---:|---:|---|---|
| Phase 1 | COMPLETE | 0 | 0 | 0 | N/A — fixture-only | 허용됨/완료 |
| CP1 | PASS | 0 | 0 | 0 | 당시 provider live semantics; 후속으로 이관 | CP2 허용됨/완료 |
| CP2 | COMPLETE | 0 | 0 | 1 deferred environment | natural 429, actual 429/5xx, 나머지 market endpoints/timing | CP3-A 허용됨/완료 |
| CP3-A | PASS — CLOSED | 0 | 0 | 0 | enum, exchange, `/stocks/all`, `/prices`, freshness/promotion evidence | CP3-B 허용됨/실행 |
| CP3-B | CHANGES REQUIRED | 0 | 2 | 2 | 위 provider semantics 그대로 | **CP3-C 불허** |
| CP3-C | NOT STARTED | N/A | N/A | N/A | 아직 평가 대상 아님 | 불허 |

## 11. Required answers

### 1. Should CP2 be reopened?

**NO.**

### 2. Should any CP3 work be reverted?

**NO.** CP3-A는 유효하고 CP3-B도 fix-forward 가능한 foundation이다. CP2 regression이나 revert가 필요한 보안 변경은 없다.

### 3. Is `a33cf6e` a valid base?

**YES — CP3-B remediation base로는 유효하다.** CP3-B complete 또는 CP3-C 시작 base로 승인된 것은 아니다.

### 4. Is CP3-B actually complete?

**NO. P1 2건이 남아 있다.**

### 5. Is CP3-C allowed to start?

**NO.**

### 6. What is the single next action?

**`a33cf6e`를 유지한 채 CP3-B remediation checkpoint 하나를 열어 source revision-chain 강제와 conflicting active VERIFIED mapping 차단을 함께 수정한 후 독립 재감사를 받는 것**이다. CP3-C는 그 전까지 시작하면 안 된다.

## 12. Audit execution boundary

strict read-only 조건 때문에 test runner, build, migration, live preflight는 실행하지 않았다. 테스트 구현과 과거 실행 보고만 검사했으며, 실제 Toss 요청과 credential 접근은 0이었다.

READ-ONLY AUDIT COMPLETE
Repository changes: 0
Commits: 0
Pushes: 0
