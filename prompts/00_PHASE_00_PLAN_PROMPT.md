# Codex에 입력할 첫 번째 프롬프트

아래 전체를 Codex 입력창에 붙여 넣습니다.

```text
/plan

이 저장소는 토스증권, OpenDART, SEC EDGAR 등을 향후 연결할 읽기 전용 기업분석 대시보드 프로젝트다.

지금은 코드를 작성하거나 수정하지 말고 Phase 0 문서 검토와 Phase 1 실행계획만 수행하라.

작업 전 반드시 다음을 읽어라.
- README_START_HERE.md
- AGENTS.md
- docs/00_MASTER_IMPLEMENTATION_PLAN.md
- docs/01_PRODUCT_REQUIREMENTS.md
- docs/02_ARCHITECTURE.md
- docs/03_DATA_SOURCES_AND_FRESHNESS.md
- docs/04_DATA_CONTRACTS.md
- docs/05_INSTITUTIONAL_FLOW_SPEC.md
- docs/06_VALUATION_SPEC.md
- docs/07_FILING_DIFF_SPEC.md
- docs/08_MACRO_COMPANY_IMPACT_SPEC.md
- docs/09_ASSETSQUARE_INTERFACE_SPEC.md
- docs/10_SECURITY_AND_OPERATIONS.md
- docs/11_ACCEPTANCE_TESTS.md
- docs/12_CODEX_WORKFLOW.md
- docs/13_UI_AND_DASHBOARD_SPEC.md
- docs/14_NEWS_AND_EVENT_SPEC.md
- plans/PHASE_01_FOUNDATION_BRIEF.md
- STATUS.md
- DECISIONS.md
- KNOWN_ISSUES.md

수행할 작업:
1. 문서 간 충돌, 모호함, 구현 불가능성, 비용 조건 위반, 보안 위험, 누락된 완료 기준을 독립적으로 검토한다.
2. 사용자 요구와 직접 관련 없는 기능 확대를 찾아 표시한다.
3. Phase 1만을 위한 상세 실행계획을 작성한다.
4. 생성·수정할 파일을 구체적으로 나열한다.
5. 기술 선택과 이유, Windows 실행 방법, 테스트 명령을 정한다.
6. fixture와 데이터 계약의 구체적 테스트 사례를 정한다.
7. Phase 1 명시적 비범위를 반복 확인한다.
8. 실패·롤백·멱등성·시크릿 검사 방법을 포함한다.
9. 완료 기준을 자동 검증 가능한 형태로 작성한다.
10. 질문이 생겨도 안전하고 합리적인 기본안을 제시하고, 막히는 항목만 OPEN QUESTION으로 남긴다.

산출물:
- plans/PHASE_01_EXECUTION_PLAN.md
- qa/PHASE_00_DOCUMENT_REVIEW.md

중요:
- 이 단계에서는 애플리케이션 코드, 설정, package 파일, DB migration을 생성하거나 수정하지 않는다.
- 기존 사양을 임의로 낮추거나 삭제하지 않는다.
- 문서 변경이 필요하면 DECISIONS.md에 넣을 PROPOSED ADR 초안을 결과에 포함하되 실제 파일은 수정하지 않는다.
- 결과 마지막에 Phase 1을 바로 구현해도 되는지 PASS / CONDITIONAL PASS / FAIL로 판정한다.
```

---

## Codex 결과를 받은 뒤

다음 파일을 이 채팅에 전달해 검토받습니다.

- `plans/PHASE_01_EXECUTION_PLAN.md`
- `qa/PHASE_00_DOCUMENT_REVIEW.md`

`PASS` 또는 승인된 `CONDITIONAL PASS` 전에는 다음 Goal을 실행하지 않습니다.
