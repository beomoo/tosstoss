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

구현 사실과 증거가 충돌할 때는 다음 우선순위로 판단한다.

1. 사용자 요구사항 / 승인 범위
2. 실제 승인된 Codex prompt
3. actual Git diff / current code / schema
4. 실제 tests / execution
5. review evidence / logs
6. 승인 architecture / plan
7. Codex 설명

이 순위는 실제 코드의 승인·계약 위반을 정당화하지 않는다.
설명과 코드가 다르면 실제 코드로 구현 사실을 판단하고,
확인할 수 없는 사항은 `NOT VERIFIED`로 기록한다.
단순 문서 표현 차이와 실제 승인 계약의 semantic conflict를 구분한다.
실제 semantic conflict가 있으면 임의 결정하지 않고 STOP한다.

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
→ affected regression
→ checkpoint가 요구하는 경우 standard full QA
→ handoff/closeout
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

승인된 구현 범위 안의 source/code 수정은 bounded self-repair 대상이 될 수 있다.
다만 승인 범위를 넘어 architecture, security/auth, schema/migration,
transaction/concurrency, data-integrity, canonical identity 또는
test/acceptance의 의미를 변경해야 하면 STOP한다.
SQL/FK/index, fixture, revision expectation 수정은 기존 승인 계약과
acceptance 의미를 유지하는 경우에만 허용한다.

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

## 6. 검증 필요성 사전 판정

모든 작업 시작 시 승인 범위와 근거 조항, 실제 변경 의미와 위험도,
기존 CLOSED 상태 및 새 변경·회귀·증거 충돌 여부를 확인한다.
아래 A/B/C 유형과 필요한 QA, 허용된 종료 상태를 짧게 명시한다.
분류는 파일 확장자나 작업 이름이 아니라 실제 영향과 checkpoint 요건에 따른다.

### A. Codex 자동 완료

읽기 전용 조사, 중간 diagnosis, 증거 탐색·수집, 경로 확인, SHA256 확인,
패키징, 단순 문서 정합성·운영지침 정리·Git closeout·staging/commit 준비는
Codex가 자체 완료한다.
단순 문서 작업은 기존 정책·승인·STOP·QA·acceptance 의미를 유지하는 경우에만 A다.
운영지침 파일이라도 실제 권한이나 검증 기준을 바꾸면 A로 자동 분류하지 않는다.
Repository source와 정책·test 의미를 바꾸지 않는 환경 문제 해결,
QA mirror drift, editable/path/tool/command/dependency setup 문제,
disposable environment·scanner preflight 복구와 source-unchanged QA 재실행도 포함한다.

GPT 독립검증을 요청하지 않으며 review ZIP/GPT 요청문을 자동 생성하지 않는다.
필요한 자체 점검과 이미 승인된 QA는 수행한다. 환경 STOP 자체는
자동 GPT 독립검증 사유가 아니다.

### B. Codex 자체 QA 후 완료

기존에 승인된 일반 구현·수정은 C 유형이나 명시적인 독립검증 요건에
해당하지 않는 한 B로 분류하고, 필요한 focused QA와 affected regression 후 자체 종료한다.
Checkpoint가 요구하는 standard full QA는 그대로 수행한다.

### C. GPT 독립검증 필요

Security/auth, schema/migration, transaction/concurrency, canonical identity,
data-integrity, 중요 regression에 영향을 주는 구현·수정 및 명시적으로
GPT 독립검증을 요구하는 checkpoint의 최종 implementation/remediation candidate,
integration 전 독립 acceptance를 C로 분류한다.
모든 일반 구현의 최종 candidate가 자동으로 C가 되는 것은 아니며,
승인된 일반 구현은 B의 QA를 충족하면 자체 종료할 수 있다.

중간 결과를 반복 검증하지 않고 안정된 최종 candidate에서 원칙적으로 한 번 검증한다.
환경 문제나 bounded self-repair 한도 소진만으로 GPT 독립검증을 자동 요청하지 않는다.
새로운 semantic/risk boundary 판단이 필요한 경우에만 GPT 판단 또는 사용자 승인을 요청한다.
독립검증이 요구된 checkpoint의 결과를 Codex 자체 QA만으로 PASS/CLOSED로
올리지 않는다. 승인되지 않은 정책 결정이나 STOP 해제는 먼저 사용자 판단을 받는다.

---

## 7. 중복 검증 금지와 상태 추적

- 이미 GPT가 CLOSED한 checkpoint는 새 변경·회귀·증거 충돌이 없으면
  재검증하지 않는다. 과거의 review-required 기록만으로 다시 열지 않는다.
- 증거 수집·경로 확인·패키징 자체는 GPT 독립검증 대상이 아니다.
  실제로 드러난 semantic/code 문제나 증거 충돌은 그 영향에 따라 분류한다.
- GPT 검증을 요청할 때는 해당 승인 조항과 실제 위험 근거,
  대상 candidate와 허용된 판정 상한을 반드시 명시한다.
  이유 없이 습관적으로 검증을 요청하지 않는다.
- DOTS는 검증 필요성 분류와 상태 추적을 담당한다.
  GPT의 PASS/FAIL이나 사용자의 위험 작업 승인을 대신하지 않는다.
- A/B 분류나 자체 종료는 구현·QA 권한을 추가하거나 acceptance를 낮추지 않는다.
  기존 안전·QA·승인·STOP 조건과 frozen boundary를 유지한다.
- 현재 C3 frozen candidate와 진행 중인 QA·worktree는 운영지침 변경으로
  수정하지 않는다. C3 final acceptance의 기존 E2/E4 검증 절차를 유지하며,
  이 문서 변경은 C3 acceptance나 후속 작업 착수 승인이 아니다.
- AGENTS.md 변경은 C3 frozen candidate의 HEAD/tree/index와 진행 중인 QA 환경을
  변경하지 않는 별도 branch/worktree에서 수행한다.
  운영지침 변경으로 기존 C3 acceptance를 자동 승인하거나 재검증하지 않는다.
  실제 현재 상태를 확인하지 않은 채 C3를 CLOSED로 가정하지 않으며,
  이미 CLOSED된 경우에도 이 문서 작업으로 재개하지 않는다.
  C3 CLOSED 후 관련 일시적 상태는 STATUS.md 등 상태 문서에서 관리한다.

---

## 8. GPT 독립검증 package

제6절에서 C로 분류되어 실제 독립검증에 제출할 때만 다음을 제공한다.
미완료·차단으로 STOP한 제출도 포함하며, A/B 작업에는 자동 적용하지 않는다.
C 유형에서도 사용자 판단이 필요한 STOP과 실제 GPT 검증 제출을 구분한다.
단순 환경 STOP, source-unchanged QA 문제, 증거 탐색이나 단순 패키징 실패만으로
review ZIP/GPT 요청문을 자동 생성하지 않는다.

```text
review ZIP
GPT_REVIEW_REQUEST.md
사용자가 그대로 붙여넣을 검증 요청문 (copy-ready verification prompt)
```

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

이전 GPT 독립검증이 있는 remediation에서는 다음을 보존한다.

```text
previous candidate SHA/tree
previous GPT verdict
previous findings
GPT가 작성한 authoritative remediation/closeout prompt
```

과거 GPT raw report 파일은 supplementary evidence이며 필수 prerequisite가 아니다.
선택적인 raw report 부재 때문에 작업을 차단하지 않는다.

시크릿·credential·production DB·민감 raw log는 제외한다.

ZIP의 파일명이 실제 내용과 맞는지 확인하며 authorization 파일을 중복/오표기하지 않는다.

---

## 9. QA

현재 checkpoint에 필요한 QA를 실제로 실행한다.

과거 전체 suite를 이유 없이 반복하지 않는다.

다음 흐름을 제3절과 동일하게 적용한다.

```text
implementation
→ focused QA
→ affected regression
→ checkpoint가 요구하는 경우 standard full QA
→ handoff/closeout
```

기존 checkpoint의 필수 QA는 생략하지 않으며 모든 단순 변경에 full QA를 새로 강제하지 않는다.
단순 문서 정합성 수정 자체에는 제품 전체 QA를 자동 실행하지 않고
필요한 문서 정합성과 변경 범위를 검증한다.

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

승인된 전체 구현계획 안에서는 checkpoint가 요구하는 QA·독립 acceptance 등
완료조건을 충족하면 다음 승인된 계획 단계로 별도 사용자 승인 없이 진행한다.
별도 승인을 요구하는 checkpoint나 기존 STOP·frozen boundary를
자동으로 해제하거나 승인 범위를 넓히는 뜻은 아니다.

예:

```text
C1 → C2
implementation → focused QA → affected regression
→ checkpoint가 요구하는 경우 standard full QA → handoff/closeout
```

단:

```text
main merge
deploy
production 작업 (DB mutation 포함)
live external authority
Trading
security/auth 또는 schema/migration 정책 변경
transaction/concurrency/data-integrity 정책 변경
canonical identity 의미 변경
test/acceptance 완화
승인 범위 확대 또는 새 architecture
승인 범위를 넘어서는 irreversible action
```

과 같은 새로운 위험 경계에서는 STOP하고 명시적 승인을 받는다.
승인 범위 안의 구현·bounded self-repair·필수 QA에는 중간 승인을 반복 요구하지 않는다.

---

## 11. 주요 보고 마지막에 현재 위치 표시

주요 보고와 모든 주요 Codex 작업 프롬프트 마지막에 다음 항목을 짧게 포함한다.

```text
현재 작업
이미 완료된 범위
전체 계획에서 현재 위치
다음 단계

권장 Model
권장 Reasoning
CLI / App
새 session / 기존 session
실행 환경
필요 시 isolation
선택 이유
```

실제 실행 가능한 모델·옵션을 사용하며 설치 환경에서 지원되지 않는 옵션을 가정하지 않는다.

---

## 12. 실행 모델 권장

### 환경·문서·QA orchestration

```text
Model: GPT-6.1 Sol
Reasoning: High
```

### 구현·bounded remediation

```text
Model: GPT-6.1 Sol
Reasoning: Extra High
```

### security/auth/schema/migration/concurrency/transaction

```text
Model: GPT-6.1 Sol
Reasoning: Extra High
```

같은 candidate의 연속 작업은 기존 세션을 재사용한다.
새 세션 인계에는 승인 범위, source identity, 실제 QA·exit code,
잔여 작업·NOT VERIFIED, 규범 문서 참조와 다음 단계를 포함한다.

새 architecture checkpoint는 새 세션을 우선한다.

고정 범위·재현 가능한 작업은 CLI를 우선 검토한다.

제12·13절의 모델·reasoning 값은 권장 설정이다.
실제 설치 환경의 지원 여부를 확인하고, 확인하지 못한 항목은 `NOT VERIFIED`로 보고한다.
Extra High는 해당 환경의 `xhigh` 옵션과의 대응을 확인한 뒤 사용한다.
문서 수정만으로 다른 실행 중인 세션의 모델이나 설정을 변경하지 않는다.

---

## 13. GPT 독립검증 권장 모드

독립검증 package가 필요한 경우 요청문 마지막에 권장 GPT 모드를 적는다.

일반 GPT 독립검증:

```text
Model: GPT-6.1 Sol
Reasoning: High
```

고위험 GPT 독립검증 (security/auth/schema/migration/concurrency/transaction):

```text
Model: GPT-6.1 Sol
Reasoning: Extra High
Fallback: High
```

Git identity/docs-only 경량 확인은 제6절의 A 유형으로 자체 종료한다.
그 과정에서 C 유형의 실제 위험이 드러난 경우에만 해당 위험의 검증 모드를 적용한다.
