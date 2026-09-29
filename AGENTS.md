# Project Instructions for Codex

## 1. 역할과 범위

현재 repository는 승인된 단계별 구현계획을 따른다.

Codex는 승인된 범위를 구현하고 bounded self-repair와 self-QA를 수행한다.

Architecture, security policy, schema meaning, transaction policy 또는 승인 범위를 임의로 변경하지 않는다.

현재 승인되지 않은:

```text
production DB mutation
public deployment
live external authority
Trading
```

은 실행하지 않는다.

기본 안전 원칙:

```text
LOCAL_ONLY=true
TRADING_ENABLED=false
DRY_RUN=true
```

---

## 2. 작업 전 확인

작업과 직접 관련된 범위에서 다음을 확인한다.

```text
README_START_HERE.md
docs/00_MASTER_IMPLEMENTATION_PLAN.md
현재 Phase plan
직접 관련 contract/spec
docs/10_SECURITY_AND_OPERATIONS.md
docs/11_ACCEPTANCE_TESTS.md
STATUS.md
DECISIONS.md
KNOWN_ISSUES.md
```

현재 세션에서 이미 확인했고 변경되지 않은 자료를 이유 없이 반복해서 읽지 않는다.

Semantic conflict가 있으면 임의 결정하지 않고 STOP한다.

---

## 3. 작업 batching

작업을 지나치게 작은 단계로 쪼개지 않는다.

### 단순 작업

다음은 가능한 한 하나의 작업 안에서 끝낸다.

```text
QA mirror/path
editable install
fixture
revision expectation
lint/type/format
disposable DB/environment
단순 문서 정합성
동일 QA 재실행
```

Architecture/security/schema/test 의미가 바뀌지 않는 한 중간 승인이나 GPT 독립검증을 반복하지 않는다.

### 고정 범위 구현

이미 architecture가 승인된 작업은 가능하면:

```text
implementation
→ focused QA
→ regression
→ full QA
→ handoff
```

까지 연속 진행한다.

### 별도 STOP이 필요한 경우

```text
new architecture
security/auth 의미 변경
schema/migration 의미 변경
transaction/data-integrity 정책 변경
test/acceptance 완화
scope 확대
production mutation
새 live external authority
```

가 필요할 때만 사용자 판단으로 돌아간다.

---

## 4. Bounded self-repair

승인 범위 안의 일반 오류는 약 2~3회:

```text
diagnose
→ minimal repair
→ rerun
```

한다.

허용 예:

```text
syntax/type/lint
fixture
SQL/FK/index
path
QA mirror
editable install
disposable environment
revision expectation
command invocation
```

단순 환경 문제 때문에 반복 STOP하지 않는다.

Repository semantics를 바꿔야 하면 STOP한다.

---

## 5. 환경/QA 복구

Repository source를 변경하지 않는 QA 환경 문제는 승인된 작업 안에서 연속 해결할 수 있다.

예:

```text
candidate → disposable mirror synchronization
editable install → exact mirror
PATH/working directory
disposable DB
temporary QA state
Git index/worktree synchronization in disposable mirror
```

조건:

- authoritative candidate를 바꾸지 않는다.
- dependency version을 임의 변경하지 않는다.
- test 의미를 바꾸지 않는다.
- scanner/policy 의미를 바꾸지 않는다.
- 복구 후 candidate와 QA 환경의 equality를 재확인한다.

---

## 6. 독립검증이 필요한 경우

정식 GPT 독립검증 package는 다음에만 만든다.

```text
최종 implementation/remediation candidate
schema/migration/security/auth/transaction 최종 candidate
integration 전 독립 acceptance가 필요한 checkpoint
semantic/code 문제로 다음 수정 범위를 GPT가 판단해야 하는 경우
```

---

## 7. 독립검증이 필요하지 않은 경우

다음에는 review ZIP/GPT 요청문을 자동 생성하지 않는다.

```text
QA mirror drift
editable/path 문제
tool/command 오류
disposable environment 문제
dependency setup 문제
read-only 중간 diagnosis
source가 바뀌지 않은 QA rerun
scanner preflight 환경 문제
단순 staging/commit 준비
```

환경 STOP은 자동 GPT 독립검증 요청이 아니다.

---

## 8. GPT 독립검증 package

실제로 필요할 때는:

```text
review ZIP
GPT_REVIEW_REQUEST.md
사용자가 그대로 붙여넣을 검증 요청문
```

을 제공한다.

필요한 범위에서 포함:

```text
user request
approved implementation/remediation prompt
base/candidate identity
actual diff
candidate source
relevant baseline
test results / exit codes
execution evidence
scope/frozen proof
manifest
self-QA
NOT VERIFIED items
```

시크릿·credential·production DB·민감 raw log는 제외한다.

ZIP의 파일명이 실제 내용과 맞는지 확인하며 authorization 파일을 중복/오표기하지 않는다.

---

## 9. QA

현재 checkpoint에 필요한 QA를 실제로 실행한다.

과거 전체 suite를 이유 없이 반복하지 않는다.

변경 영향 regression을 수행하고 final checkpoint가 요구하면 standard full QA를 수행한다.

테스트를:

```text
삭제
skip
xfail
assertion 완화
조건부 우회
```

해서 통과시키지 않는다.

---

## 10. 완료 및 자동 진행

승인된 전체 구현계획 안에서는 checkpoint가 정상 완료되면 다음 계획된 checkpoint로 별도 사용자 승인 없이 진행할 수 있다.

예:

```text
C1 → C2
implementation → focused → regression → full QA
```

단:

```text
main merge
deploy
production DB mutation
live external authority
Trading
승인 범위를 넘어서는 irreversible action
```

은 자동 진행하지 않는다.

계획 자체가 달라질 때만 STOP한다.

---

## 11. 주요 보고 마지막에 현재 위치 표시

항상 짧게 적는다.

```text
지금 하는 작업
현재까지 완료된 범위
전체 계획에서 현재 위치
다음 단계
```

---

## 12. 실행 모델 권장

### 환경·문서·QA orchestration

```text
Model: Astra
Reasoning: Medium
```

### 구현·bounded remediation

```text
Model: Astra
Reasoning: High
```

### security/auth/schema/migration/concurrency/transaction

```text
Model: Astra
Reasoning: High
```

같은 candidate의 연속 작업은 기존 세션을 재사용한다.

새 architecture checkpoint는 새 세션을 우선한다.

고정 범위·재현 가능한 작업은 CLI를 우선 검토한다.

---

## 13. GPT 독립검증 권장 모드

독립검증 package가 필요한 경우 요청문 마지막에 권장 GPT 모드를 적는다.

일반 구현:

```text
GPT-5.6 Sol
Thinking: High
```

Security/auth/migration/concurrency:

```text
GPT-5.6 Sol
Thinking: Extra High 가능 시
Fallback: High
```

Git identity/docs-only 경량 확인:

```text
GPT-5.6 Sol
Thinking: Medium
```
