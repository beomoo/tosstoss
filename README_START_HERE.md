# 토스증권 기업분석 대시보드 — Codex 시작 안내

- 문서 버전: `0.1.0`
- 작성 기준일: `2026-08-16`
- 현재 목표: **로컬에서 실행되는 읽기 전용 투자분석 대시보드의 기반을 단계적으로 구축**
- 현재 비범위: 공개 인터넷 배포, 실제 주문, 자동매매, OpenAI API 자동 호출, 유료 데이터 API
- 장기 방향: 별도 승인된 공개 읽기 전용 대시보드와 별도 승인된 자동매매 프로젝트를 현재 로컬 구현과 분리

이 저장소 문서 묶음은 Codex가 전체 방향을 알고 설계하되, **한 번에 전체 기능을 만들지 않고 Phase별로 구현·검증**하도록 구성되어 있습니다.

장기 방향은 현재 권한을 넓히지 않습니다. 현재 작업은 계속 `LOCAL_ONLY=true`, `TRADING_ENABLED=false`, `DRY_RUN=true`이며, 공개 읽기 전용 배포와 거래는 각각 독립된 미래 체크포인트와 명시적 승인이 필요합니다.

---

## 1. 가장 먼저 할 일

1. 이 묶음의 폴더 구조를 그대로 새 프로젝트 저장소 루트에 복사합니다.
2. 저장소 이름은 예를 들어 `toss-invest-research-dashboard`로 정합니다.
3. 가능하면 비공개 GitHub 저장소로 만듭니다.
4. Codex에서 해당 저장소 폴더를 엽니다.
5. 첫 작업에서는 API 키를 넣지 않습니다.
6. `prompts/00_PHASE_00_PLAN_PROMPT.md`의 내용을 Codex에 입력합니다.
7. Codex가 계획과 문서 QA를 만들면 **코딩을 시작하지 말고** 결과를 먼저 검토합니다.

---

## 2. 문서 구조

```text
AGENTS.md
README_START_HERE.md
STATUS.md
DECISIONS.md
KNOWN_ISSUES.md
CHANGELOG.md

docs/
├─ 00_MASTER_IMPLEMENTATION_PLAN.md
├─ 01_PRODUCT_REQUIREMENTS.md
├─ 02_ARCHITECTURE.md
├─ 03_DATA_SOURCES_AND_FRESHNESS.md
├─ 04_DATA_CONTRACTS.md
├─ 05_INSTITUTIONAL_FLOW_SPEC.md
├─ 06_VALUATION_SPEC.md
├─ 07_FILING_DIFF_SPEC.md
├─ 08_MACRO_COMPANY_IMPACT_SPEC.md
├─ 09_ASSETSQUARE_INTERFACE_SPEC.md
├─ 10_SECURITY_AND_OPERATIONS.md
├─ 11_ACCEPTANCE_TESTS.md
├─ 12_CODEX_WORKFLOW.md
├─ 13_UI_AND_DASHBOARD_SPEC.md
└─ 14_NEWS_AND_EVENT_SPEC.md

plans/
└─ PHASE_01_FOUNDATION_BRIEF.md

prompts/
├─ 00_PHASE_00_PLAN_PROMPT.md
├─ 01_PHASE_01_GOAL_PROMPT.md
└─ 02_PHASE_01_INDEPENDENT_REVIEW_PROMPT.md

templates/
└─ PHASE_QA_TEMPLATE.md
```

---

## 3. 이 묶음을 쓰는 원칙

- 전체 문서는 처음부터 저장소에 둡니다.
- 구현은 하나의 대형 작업이 아니라 **한 Phase씩** 진행합니다.
- 각 Phase는 `/plan → 계획 검토 → /goal → 자체 QA → 독립 리뷰 → 통합 QA` 순서로 진행합니다.
- Codex가 사양을 편의대로 바꾸지 못하게 합니다.
- 누락 데이터는 `0`이 아니라 `null`과 사유로 저장합니다.
- 수집일, 기준일, 발표일, 정정일을 서로 구분합니다.
- 실제 투자 판단보다 **데이터 정확성, 출처, 변경 이력**을 먼저 완성합니다.
- 주문 관련 코드는 현재 단계에서 만들지 않습니다.

---

## 4. 첫 번째 완료 지점

Phase 1이 끝났다고 인정하려면 최소한 다음이 모두 충족되어야 합니다.

- Next.js 프론트엔드와 FastAPI 백엔드가 로컬에서 실행됩니다.
- 실제 외부 API 없이 fixture 데이터만 사용합니다.
- 시크릿이 프론트엔드나 로그에 노출되지 않습니다.
- SQLite 마이그레이션이 재실행 가능하고 멱등적입니다.
- 핵심 데이터 계약의 샘플 JSON이 생성됩니다.
- lint, typecheck, unit test, integration test, build가 통과합니다.
- `qa/PHASE_01_SELF_QA.md`, `STATUS.md`, `CHANGELOG.md`가 갱신됩니다.
- 실제 주문 기능과 OpenAI API 호출은 존재하지 않습니다.

---

## 5. 사용자가 준비할 API 키

키는 **Phase 1 완료 후**, 실제 API 연결 단계에서만 준비합니다.

```text
토스증권 Open API
OpenDART API
선택: OpenFIGI API
선택: 뉴스 검색 API
```

실제 값은 채팅, 문서, GitHub에 올리지 않습니다. 향후 로컬 `.env`에만 저장합니다.

---

## 6. 지금 실행할 파일

첫 실행:

```text
prompts/00_PHASE_00_PLAN_PROMPT.md
```

계획 승인 후 실행:

```text
prompts/01_PHASE_01_GOAL_PROMPT.md
```

Phase 1 구현 후 별도 Codex 채팅에서 실행:

```text
prompts/02_PHASE_01_INDEPENDENT_REVIEW_PROMPT.md
```

---

## 7. 중요한 주의사항

이 시스템의 목적은 자료를 정확히 수집·비교하고 투자 가설을 검증하는 것입니다.  
기관의 13F 보유 증가, 기술적 지표, 기사, 공시 문구 하나만으로 매수·매도 결론을 내리지 않습니다.

자산제곱 사고모형은 Phase 1에서 자동 구현하지 않습니다. 다만 이후 연결을 위해 근거, 반대 근거, 가설, 무효화 조건, 시나리오 변경 이력의 데이터 구조는 처음부터 고려합니다.
