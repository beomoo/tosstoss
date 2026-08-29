# VALIDATION_CHECKLIST.md

# Codex Implementation Validation Checklist

이 문서는 Codex가 구현한 작업을 검증하기 위한 공통 체크리스트다.

사용 목적은 두 가지다.

1. Codex가 작업 완료 전에 수행하는 자기검증
2. ChatGPT가 GitHub의 실제 코드와 Git diff를 기준으로 수행하는 독립 최종검증

Codex의 자기검증 결과는 최종 검증을 대체하지 않는다.

ChatGPT는 Codex의 완료 보고 또는 자기평가를 그대로 신뢰하지 않고 실제 코드, Git diff, 테스트 및 실행 경로를 기준으로 독립적으로 재검증한다.

---

# 0. 검증 기준 우선순위

검증 기준은 다음 순서를 따른다.

1. 사용자의 원래 요구사항
2. ChatGPT가 작성한 Codex 작업 프롬프트
3. Codex가 작업 전에 제시한 구현계획
4. 실제 GitHub 코드와 Git diff
5. 테스트 및 실행 결과
6. Codex의 완료 보고

Codex가 자신의 구현계획을 모두 수행했더라도 구현계획 자체가 원래 요구사항이나 작업 프롬프트를 누락했다면 완료로 판단하지 않는다.

---

# 1. 검증 대상 기록

검증을 시작하기 전에 다음 정보를 확인한다.

- [ ] 검증 대상 작업이 무엇인지 명확하다.
- [ ] 사용자의 원래 요구사항을 확인했다.
- [ ] 해당 작업의 Codex 프롬프트를 확인했다.
- [ ] Codex가 제시한 구현계획을 확인했다.
- [ ] 검증 대상 branch 또는 commit을 확인했다.
- [ ] 작업 시작 전 기준 commit을 확인할 수 있다.
- [ ] 작업 완료 후 commit을 확인할 수 있다.
- [ ] 비교해야 할 Git diff 범위가 명확하다.
- [ ] Codex 완료 보고가 있다면 참고자료로 확보했다.

가능하면 검증 기록에 다음을 남긴다.

```text
Task:
Base commit:
Target commit:
Branch:
Codex prompt:
Implementation plan:
Validation date:
Validator:
```

---

# 2. Requirement Traceability

각 주요 요구사항을 실제 구현까지 추적한다.

가능하면 다음 구조로 기록한다.

| ID | 원래 요구사항 | Codex 프롬프트 | 구현계획 | 실제 코드 | 테스트 | 판정 |
|---|---|---|---|---|---|---|
| R1 | | | | | | PASS / PARTIAL / FAIL / NOT VERIFIED |

다음을 확인한다.

- [ ] 사용자의 모든 필수 요구사항이 목록화되어 있다.
- [ ] 각 요구사항이 Codex 작업 프롬프트에 반영되어 있다.
- [ ] Codex가 요구사항을 임의로 축소하지 않았다.
- [ ] Codex가 요구사항을 임의로 다른 기능으로 대체하지 않았다.
- [ ] 구현계획에 각 주요 요구사항이 포함되어 있다.
- [ ] 요구사항별 실제 구현 코드가 존재한다.
- [ ] 코드가 존재하기만 하는 것이 아니라 실제 실행 경로에 연결되어 있다.
- [ ] UI만 만들고 backend 또는 data layer가 빠진 기능이 없다.
- [ ] backend만 만들고 실제 API/UI에서 사용하지 않는 기능이 없다.
- [ ] dead code 형태로만 구현된 기능이 없다.
- [ ] Codex가 구현 완료라고 보고했지만 실제 코드에 없는 기능이 없다.
- [ ] 요구사항을 부분적으로만 구현한 경우 PARTIAL로 표시했다.
- [ ] 직접 검증하지 못한 요구사항을 PASS 처리하지 않았다.

---

# 3. Codex 작업 프롬프트 이행

ChatGPT가 작성한 Codex 작업 프롬프트의 모든 필수 항목을 실제 구현과 대조한다.

- [ ] 프롬프트의 모든 MUST 요구사항을 확인했다.
- [ ] 필수 기능이 모두 구현되었다.
- [ ] 금지된 구현 방식이 사용되지 않았다.
- [ ] 기존 기능을 유지하라는 조건이 지켜졌다.
- [ ] 수정 금지 영역을 건드리지 않았다.
- [ ] 특정 데이터 소스를 사용하라는 요구가 지켜졌다.
- [ ] 특정 API 또는 데이터 계약을 유지하라는 요구가 지켜졌다.
- [ ] 테스트 작성 또는 실행 요구가 지켜졌다.
- [ ] mock 금지 요구가 지켜졌다.
- [ ] hard-coded data 금지 요구가 지켜졌다.
- [ ] 임시 fallback 금지 요구가 지켜졌다.
- [ ] Acceptance Criteria가 모두 충족되었다.

프롬프트 항목이 구현계획에서 누락되었더라도 최종 검증에서는 누락으로 판정한다.

---

# 4. Codex 구현계획 이행

Codex의 승인된 구현계획과 실제 코드를 비교한다.

- [ ] 계획한 기능이 모두 구현되었다.
- [ ] 계획한 파일이 실제로 생성 또는 수정되었다.
- [ ] 계획한 API가 구현되었다.
- [ ] 계획한 data flow가 구현되었다.
- [ ] 계획한 schema 또는 migration이 구현되었다.
- [ ] 계획한 validation이 구현되었다.
- [ ] 계획한 error handling이 구현되었다.
- [ ] 계획한 테스트가 실제로 작성되었다.
- [ ] 계획한 테스트가 실행되었다.
- [ ] 계획한 frontend 연결이 완료되었다.
- [ ] 계획한 backend 연결이 완료되었다.
- [ ] 구현 도중 특정 단계를 조용히 생략하지 않았다.
- [ ] 구현계획에서 벗어난 구조적 변경이 있다면 이유를 확인했다.

구현계획 변경이 있었다면 다음 중 하나로 분류한다.

- [ ] 합리적인 계획 변경
- [ ] 필수적인 부수 변경
- [ ] 설명되지 않은 변경
- [ ] 비인가 범위 변경

---

# 5. Git Diff 전체 검토

최종 코드만 확인하지 말고 가능한 경우 반드시 작업 전후 Git diff를 확인한다.

## 변경 파일

- [ ] 새로 추가된 파일을 모두 확인했다.
- [ ] 수정된 파일을 모두 확인했다.
- [ ] 삭제된 파일을 모두 확인했다.
- [ ] rename 또는 move된 파일을 확인했다.
- [ ] 예상하지 못한 파일 변경이 없는지 확인했다.

## 삭제

특히 삭제된 코드를 주의해서 확인한다.

- [ ] 기존 기능이 삭제되지 않았다.
- [ ] 기존 validation이 삭제되지 않았다.
- [ ] 기존 error handling이 삭제되지 않았다.
- [ ] 기존 security check가 삭제되지 않았다.
- [ ] 기존 테스트가 삭제되지 않았다.
- [ ] 기존 logging/monitoring이 불필요하게 제거되지 않았다.

## 변경 규모

- [ ] 작업 요구사항과 비교해 변경 규모가 합리적이다.
- [ ] 불필요한 대규모 formatting 변경이 없다.
- [ ] unrelated cleanup이 없다.
- [ ] unrelated refactoring이 없다.
- [ ] 대규모 파일 이동이 필요 없이 발생하지 않았다.

---

# 6. Change Scope Integrity

Codex가 요구받은 범위를 넘어 기존 시스템을 임의로 변경했는지 확인한다.

각 변경을 다음 세 가지로 분류한다.

### A. 계획된 변경

원래 요구사항 또는 구현계획에 포함된 변경.

### B. 정당한 부수 변경

계획에는 직접 적혀 있지 않지만 해당 기능을 구현하기 위해 필요한 최소 변경.

### C. 비인가 범위 변경

현재 요구사항과 직접 관계없는 변경.

다음을 반드시 확인한다.

- [ ] 구현계획에 없던 파일 변경의 이유를 확인했다.
- [ ] 기존 기능의 동작을 임의로 변경하지 않았다.
- [ ] 기존 API contract를 불필요하게 변경하지 않았다.
- [ ] DB schema를 계획 없이 변경하지 않았다.
- [ ] shared type/interface를 불필요하게 변경하지 않았다.
- [ ] dependency를 불필요하게 추가하지 않았다.
- [ ] dependency를 불필요하게 삭제하지 않았다.
- [ ] dependency version을 불필요하게 upgrade하지 않았다.
- [ ] lock file 대규모 변경의 원인을 확인했다.
- [ ] configuration을 불필요하게 변경하지 않았다.
- [ ] `.env` 구조를 불필요하게 변경하지 않았다.
- [ ] CI/CD를 불필요하게 변경하지 않았다.
- [ ] Docker 설정을 불필요하게 변경하지 않았다.
- [ ] deployment 설정을 불필요하게 변경하지 않았다.
- [ ] authentication을 불필요하게 변경하지 않았다.
- [ ] authorization을 불필요하게 변경하지 않았다.
- [ ] 기존 테스트 assertion을 약화하지 않았다.
- [ ] 오류를 숨기기 위한 fallback을 추가하지 않았다.
- [ ] 현재 작업과 관계없는 UI 변경을 하지 않았다.

비인가 변경이 발견되면 파일과 변경 내용을 구체적으로 기록한다.

---

# 7. Minimal Change Principle

Codex는 현재 요구사항을 충족하기 위한 최소 범위만 수정했는지 확인한다.

- [ ] 요청하지 않은 architecture 개선을 동시에 하지 않았다.
- [ ] 요청하지 않은 리팩터링을 하지 않았다.
- [ ] 요청하지 않은 dependency 정리를 하지 않았다.
- [ ] 요청하지 않은 naming 변경을 하지 않았다.
- [ ] 요청하지 않은 folder restructuring을 하지 않았다.
- [ ] 관련 없는 코드 style 변경을 하지 않았다.
- [ ] 현재 기능과 직접 관련 없는 기존 코드를 재작성하지 않았다.

더 좋은 구조가 존재한다는 이유만으로 현재 작업과 무관한 시스템을 임의로 수정해서는 안 된다.

---

# 8. Regression 검증

새 기능이 동작해도 기존 기능을 깨뜨렸다면 완전한 PASS가 아니다.

- [ ] 기존 주요 기능이 정상 동작한다.
- [ ] 기존 API endpoint가 유지된다.
- [ ] 기존 API response contract가 유지된다.
- [ ] 기존 frontend가 정상 동작한다.
- [ ] 기존 데이터 ingestion이 정상 동작한다.
- [ ] 기존 processing pipeline이 정상 동작한다.
- [ ] 기존 database 데이터와 호환된다.
- [ ] 기존 테스트가 통과한다.
- [ ] 새로운 dependency가 기존 환경과 충돌하지 않는다.
- [ ] 기존 configuration과 호환된다.
- [ ] 기존 데이터 의미가 새 구현으로 변경되지 않았다.
- [ ] backward compatibility가 필요한 부분이 유지된다.

직접 regression test를 실행하지 못했다면 해당 영역을 NOT VERIFIED로 표시한다.

---

# 9. End-to-End 연결 검증

기능 존재만으로 구현 완료로 판단하지 않는다.

가능하면 다음 전체 흐름을 검증한다.

```text
External source / API
        ↓
Ingestion
        ↓
Validation
        ↓
Storage
        ↓
Transformation / Processing
        ↓
Analysis
        ↓
Backend / API
        ↓
Frontend
        ↓
User-visible result
```

각 단계에 대해 확인한다.

- [ ] 실제 데이터 소스와 연결된다.
- [ ] ingestion이 실제로 실행된다.
- [ ] 데이터 validation이 존재한다.
- [ ] 저장이 정상적으로 이루어진다.
- [ ] processing이 정상적으로 실행된다.
- [ ] backend/API에서 결과를 사용할 수 있다.
- [ ] frontend에서 실제 API 결과를 사용한다.
- [ ] 사용자 화면에 최종 결과가 표시된다.
- [ ] 중간 단계가 mock으로 대체되어 있지 않다.
- [ ] 데이터가 어느 단계에서 끊기지 않는다.

---

# 10. Error / Failure Handling

정상 상황뿐 아니라 실패 상황을 확인한다.

가능한 경우 다음을 검증한다.

- [ ] API timeout
- [ ] HTTP 오류
- [ ] rate limit
- [ ] authentication failure
- [ ] invalid response
- [ ] malformed response
- [ ] empty response
- [ ] null data
- [ ] partial data
- [ ] network failure
- [ ] DB failure
- [ ] duplicate data
- [ ] retry failure
- [ ] upstream source unavailable

다음을 특히 확인한다.

- [ ] 오류를 조용히 무시하지 않는다.
- [ ] `catch {}` 같은 silent failure가 없다.
- [ ] 실패 시 fake success를 반환하지 않는다.
- [ ] stale data를 최신 데이터처럼 반환하지 않는다.
- [ ] 실제 오류가 fallback에 의해 숨겨지지 않는다.

---

# 11. 임시 구현 탐지

운영 코드에서 다음을 검색한다.

```text
TODO
FIXME
TEMP
temporary
placeholder
mock
fake
dummy
hardcoded
fallback
stub
not implemented
```

그리고 다음을 확인한다.

- [ ] mock data가 운영 경로에 없다.
- [ ] fake response가 없다.
- [ ] placeholder 값이 없다.
- [ ] hard-coded 시장 데이터가 없다.
- [ ] 테스트 통과만을 위한 특수 분기가 없다.
- [ ] 임시 fallback이 운영 코드에 남지 않았다.
- [ ] TODO/FIXME가 핵심 기능에 남지 않았다.
- [ ] 미구현 코드가 정상 구현처럼 노출되지 않는다.

---

# 12. 테스트 품질 검증

테스트가 존재한다는 사실 자체는 PASS의 근거가 아니다.

- [ ] 테스트가 실제 요구사항을 검증한다.
- [ ] 단순 함수 호출 여부만 테스트하지 않는다.
- [ ] 결과 값을 의미 있게 검증한다.
- [ ] happy path가 검증된다.
- [ ] failure path가 검증된다.
- [ ] null/empty 상태가 검증된다.
- [ ] malformed data가 검증된다.
- [ ] API failure가 검증된다.
- [ ] boundary condition이 필요한 경우 검증된다.
- [ ] regression test가 필요한 경우 추가되었다.
- [ ] 기존 테스트를 삭제하지 않았다.
- [ ] 기존 assertion을 약화시키지 않았다.
- [ ] snapshot을 무분별하게 갱신하지 않았다.
- [ ] mock이 실제 오류를 가리지 않는다.

Codex가 "all tests pass"라고 보고했더라도 실제 테스트 내용과 가능한 경우 실행 결과를 확인한다.

---

# 13. 보안 검증

- [ ] API key가 코드에 포함되지 않았다.
- [ ] access token이 코드에 포함되지 않았다.
- [ ] secret이 repository에 commit되지 않았다.
- [ ] 실제 `.env` 값이 commit되지 않았다.
- [ ] credential이 log에 출력되지 않는다.
- [ ] client side에 노출되면 안 되는 key가 노출되지 않는다.
- [ ] 외부 입력 validation이 적절하다.
- [ ] authentication이 필요한 endpoint가 보호된다.
- [ ] authorization 검사가 유지된다.
- [ ] 외부 API response를 무조건 신뢰하지 않는다.

Secret 노출은 높은 우선순위 문제로 취급한다.

---

# 14. 데이터 정확성 검증

투자 데이터 프로젝트에서는 UI보다 데이터 정확성을 우선한다.

- [ ] 실제 source가 명확하다.
- [ ] source identifier 또는 URL을 추적할 수 있다.
- [ ] source timestamp가 존재한다.
- [ ] ingestion timestamp가 존재한다.
- [ ] processing timestamp가 필요한 경우 존재한다.
- [ ] last successful update를 알 수 있다.
- [ ] freshness 판단이 가능하다.
- [ ] stale 상태를 구분할 수 있다.
- [ ] 데이터 단위가 정확하다.
- [ ] currency가 정확하다.
- [ ] timezone이 명확하다.
- [ ] 날짜 기준이 명확하다.
- [ ] 동일 데이터 중복 처리가 방지되어 있다.
- [ ] 계산값의 원천 데이터를 추적할 수 있다.
- [ ] 데이터가 오래됐는데 최신처럼 표시되지 않는다.

---

# 15. 실시간 / 준실시간 데이터 검증

실시간 대시보드 또는 주기적 데이터에서는 다음을 확인한다.

- [ ] 예상 업데이트 주기가 정의되어 있다.
- [ ] 마지막 성공 업데이트 시각을 확인할 수 있다.
- [ ] 데이터 age를 확인할 수 있다.
- [ ] freshness threshold가 존재하거나 판단 가능하다.
- [ ] stale threshold가 존재하거나 판단 가능하다.
- [ ] 최신 업데이트 실패 여부를 알 수 있다.
- [ ] 이전 데이터 fallback 사용 여부를 알 수 있다.
- [ ] 오래된 fallback을 최신 데이터처럼 표시하지 않는다.
- [ ] update failure가 사용자 또는 monitoring에 드러난다.

---

# 16. 13F / 기관 포지션 데이터 검증

13F는 실시간 수급 데이터가 아니다.

반드시 다음을 구분한다.

- [ ] reporting period
- [ ] filing date
- [ ] ingestion date

다음을 확인한다.

- [ ] 분기말 보유 데이터와 제출일을 혼동하지 않는다.
- [ ] 13F 데이터가 실시간 기관 매매처럼 표현되지 않는다.
- [ ] 이전 reporting period와 정확히 비교한다.
- [ ] 신규 편입을 올바르게 계산한다.
- [ ] 전량 매도를 올바르게 계산한다.
- [ ] 비중 확대를 올바르게 계산한다.
- [ ] 비중 축소를 올바르게 계산한다.
- [ ] 기관별 position 변화가 정확하다.
- [ ] security identifier 매핑 오류 가능성을 처리한다.
- [ ] stock split 등 corporate action 영향을 고려해야 하는 경우 처리한다.
- [ ] 중복 filing 또는 amendment 처리 방법이 존재한다.
- [ ] amendment를 원 filing과 잘못 중복 계산하지 않는다.

기관 변화 분석에서는 가능하면 다음이 정확히 계산되는지 확인한다.

- 신규 편입
- 전량 매도
- shares 증가/감소
- portfolio weight 변화
- 상위 보유 종목 변화
- sector allocation 변화
- 여러 기관의 동시 방향 변화

---

# 17. API / 외부 데이터 Source 검증

- [ ] 공식 API 또는 승인된 source를 사용한다.
- [ ] source provenance가 명확하다.
- [ ] API response schema 변경에 대비한다.
- [ ] pagination을 누락하지 않는다.
- [ ] rate limit을 고려한다.
- [ ] retry 정책이 적절하다.
- [ ] timeout이 설정되어 있다.
- [ ] API key 관리가 안전하다.
- [ ] partial response를 전체 데이터처럼 처리하지 않는다.
- [ ] 실패한 source를 정상 source처럼 기록하지 않는다.

---

# 18. Storage / Database 검증

DB를 사용하는 변경의 경우 확인한다.

- [ ] schema 변경이 요구사항에 필요한 변경이다.
- [ ] migration이 존재한다.
- [ ] migration이 기존 데이터에 안전하다.
- [ ] destructive migration이 없는지 확인했다.
- [ ] unique constraint가 필요한 데이터에 존재한다.
- [ ] duplicate ingestion 가능성을 통제한다.
- [ ] timestamp가 적절하게 저장된다.
- [ ] timezone 처리가 일관된다.
- [ ] NULL 처리 정책이 명확하다.
- [ ] 기존 row와 호환된다.
- [ ] rollback 위험을 확인했다.

---

# 19. Frontend 검증

- [ ] 실제 backend/API 데이터를 사용한다.
- [ ] hard-coded sample data를 사용하지 않는다.
- [ ] loading 상태가 존재한다.
- [ ] error 상태가 존재한다.
- [ ] empty 상태가 존재한다.
- [ ] stale 상태를 표시해야 할 경우 표시한다.
- [ ] 데이터 timestamp가 필요한 경우 표시한다.
- [ ] 숫자 단위가 정확하다.
- [ ] 통화 단위가 정확하다.
- [ ] 증감 방향 표시가 실제 값과 일치한다.
- [ ] 기존 화면을 불필요하게 변경하지 않았다.

---

# 20. Architecture 검증

현재 작업의 범위 안에서 다음을 확인한다.

- [ ] 기존 architecture와 일관된다.
- [ ] business logic이 UI에 과도하게 들어가지 않았다.
- [ ] 동일 logic이 여러 파일에 복제되지 않았다.
- [ ] provider-specific logic과 domain logic이 필요 이상으로 결합되지 않았다.
- [ ] 테스트하기 어려운 구조로 변경되지 않았다.
- [ ] 하나의 거대한 파일에 기능을 몰아넣지 않았다.
- [ ] 새 기능이 기존 모듈 간 coupling을 과도하게 증가시키지 않았다.

다만 architecture 개선이 필요하다는 이유만으로 현재 요구사항과 무관한 대규모 리팩터링을 하는 것은 허용하지 않는다.

---

# 21. 최종 변경 파일 감사

검증 종료 전 변경된 파일을 다시 한 번 전체 확인한다.

각 파일을 다음 중 하나로 표시한다.

| 파일 | 분류 | 이유 |
|---|---|---|
| | 계획된 변경 / 정당한 부수 변경 / 비인가 변경 | |

- [ ] 모든 변경 파일이 위 표에 분류되었다.
- [ ] 설명할 수 없는 파일 변경이 없다.
- [ ] 비인가 변경이 없는지 최종 확인했다.

---

# 22. 최종 필수 질문

최종 PASS 전에 반드시 다음 질문에 답한다.

### Requirement

- [ ] 사용자의 원래 요구사항이 빠짐없이 구현되었는가?

### Prompt

- [ ] ChatGPT가 작성한 Codex 작업 프롬프트의 필수 요구사항이 모두 구현되었는가?

### Plan

- [ ] Codex가 승인된 구현계획을 실제 코드에 반영했는가?

### Scope

- [ ] Codex가 구현계획 외 기존 시스템을 불필요하게 변경하지 않았는가?

### Regression

- [ ] 새 구현으로 인해 기존 기능이 깨지지 않았는가?

### Reality

- [ ] 기능이 실제 데이터와 실제 실행 경로에서 동작하는가?

### Testing

- [ ] 테스트가 요구사항과 실패 상황을 의미 있게 검증하는가?

### Data

- [ ] 데이터의 정확성, freshness, provenance에 중대한 문제가 없는가?

위 질문 중 중요한 항목에 NO 또는 NOT VERIFIED가 존재하면 근거 없이 최종 PASS를 부여하지 않는다.

---

# 23. 문제 등급

발견된 문제는 다음 기준으로 분류한다.

## P0 — Critical

서비스 또는 데이터의 신뢰성을 즉시 깨뜨리는 문제.

예:

- 심각하게 잘못된 투자 데이터
- 데이터 손실
- credential/secret 노출
- 핵심 서비스 전체 장애

## P1 — High

핵심 요구사항 누락 또는 기존 주요 기능 Regression.

예:

- 필수 기능 미구현
- 핵심 계산 오류
- 중요 데이터 freshness 오류
- 비인가 핵심 시스템 변경
- 기존 중요 기능 파손

## P2 — Medium

기능은 동작하지만 안정성, 구조, 테스트, 성능 또는 유지보수상 중요한 문제가 존재.

## P3 — Low

naming, documentation, minor UX, code quality 등의 개선사항.

---

# 24. 최종 판정

다음 중 하나로 판정한다.

## PASS

원래 요구사항과 Codex 프롬프트가 충족되었고 구현계획이 이행되었으며 비인가 범위 변경이나 중대한 Regression이 발견되지 않았다.

## PASS WITH ISSUES

핵심 요구사항은 충족했지만 P2/P3 수준 문제 또는 제한적인 미검증 사항이 존재한다.

P1 문제가 있는 경우 원칙적으로 완전한 PASS를 부여하지 않는다.

## FAIL

다음과 같은 문제가 존재한다.

- 핵심 요구사항 미구현
- Codex 프롬프트 주요 항목 누락
- 구현계획 주요 단계 미완료
- 비인가 범위 변경
- 중요한 Regression
- 중대한 데이터 오류
- 실제 실행 경로 미연결
- mock/placeholder에 의존한 핵심 기능

## NOT VERIFIED

검증에 필요한 코드, diff, 테스트 또는 실행 환경이 부족하여 충분히 판단할 수 없다.

검증하지 못한 내용을 추측하여 PASS 처리하지 않는다.

---

# 25. 최종 검증 보고 형식

최종 검증 결과는 가능하면 아래 형식을 따른다.

```markdown
# Final Validation Report

## 1. 최종 판정
PASS / PASS WITH ISSUES / FAIL / NOT VERIFIED

## 2. 요구사항 충족
- R1:
- R2:
- R3:

PASS:
PARTIAL:
FAIL:
NOT VERIFIED:

## 3. Codex 프롬프트 이행
- ...

## 4. Codex 구현계획 이행
- ...

## 5. 계획 외 변경
### 계획된 변경
- ...

### 정당한 부수 변경
- ...

### 비인가 범위 변경
- ...

## 6. Regression
- ...

## 7. 테스트 및 실제 실행
- ...

## 8. 데이터 신뢰성
- source:
- timestamp:
- freshness:
- stale handling:
- provenance:

## 9. 발견된 문제

### P0
- ...

### P1
- ...

### P2
- ...

### P3
- ...

## 10. 검증하지 못한 항목
- ...

## 11. 최종 결론
- ...

## 12. Codex 수정 필요 여부
YES / NO
```

---

# 26. Codex 수정 프롬프트 작성 규칙

FAIL 또는 수정이 필요한 문제가 발견되면 Codex에게 전달할 수정 프롬프트에는 가능한 경우 다음을 포함한다.

```text
문제:
근거:
영향:
원래 기대 동작:
수정 목표:
수정해야 하는 파일/영역:
건드리면 안 되는 영역:
Acceptance Criteria:
필수 테스트:
Regression 확인:
완료 후 보고할 내용:
```

특히 다음 문구를 포함하는 것을 원칙으로 한다.

> 현재 문제를 수정하기 위해 필요한 최소 범위만 변경하라.  
> 이번 수정과 관계없는 기존 코드, architecture, dependency, configuration, API contract 또는 UI를 변경하지 마라.  
> 계획 외 변경이 불가피한 경우 변경하기 전에 그 이유와 필요성을 명확히 설명하라.

---

# 27. Codex 자기검증 시 추가 요구사항

Codex는 작업 완료 전에 이 문서를 기준으로 자기검증을 수행할 수 있다.

완료 보고에는 최소한 다음을 포함한다.

- 구현한 요구사항 목록
- 변경 파일 전체 목록
- 각 파일을 변경한 이유
- 구현계획 대비 변경사항
- 계획 외 변경 여부
- 실행한 테스트
- 테스트 결과
- 기존 기능 Regression 확인 결과
- mock / placeholder / fallback 사용 여부
- 미검증 항목
- 남아 있는 위험

Codex가 모든 항목을 PASS라고 보고하더라도 ChatGPT의 독립 최종검증을 대체하지 않는다.

---

# 28. ChatGPT 독립검증 원칙

ChatGPT는 최종 검증에서 다음 원칙을 따른다.

- Codex 자기평가를 증거로 취급하지 않는다.
- 실제 GitHub 코드와 Git diff를 우선한다.
- 원래 요구사항을 구현계획보다 우선한다.
- 계획 외 변경을 별도로 감사한다.
- 삭제된 코드도 반드시 검토한다.
- 테스트 코드 자체의 품질도 검토한다.
- 실행하지 못한 항목은 NOT VERIFIED로 표시한다.
- 중요한 판정에는 가능한 경우 파일, 함수, diff, 테스트 등의 근거를 제시한다.

최종 PASS는 단순히 테스트가 통과했다는 이유만으로 부여하지 않는다.

---

# 최종 원칙

이 체크리스트의 목적은 Codex가 많은 코드를 작성했는지를 평가하는 것이 아니다.

최종적으로 확인해야 하는 것은 다음이다.

**Codex가 사용자의 원래 요구사항과 작업 프롬프트를 빠짐없이 정확하게 구현했는가?**

**승인된 구현계획을 실제 코드에 반영했는가?**

**기능 구현과 관계없는 기존 시스템을 임의로 변경하지 않았는가?**

**새로운 구현 때문에 기존 기능에 Regression이 발생하지 않았는가?**

**실제 데이터와 실행 경로에서 기능이 정상적으로 동작하는가?**

위 질문에 실제 코드, Git diff, 테스트 및 실행 결과를 근거로 답할 수 있을 때 작업 완료 여부를 판단한다.
