# Phase 1 계획 승인 후 Codex에 입력할 프롬프트

`plans/PHASE_01_EXECUTION_PLAN.md`가 검토·승인된 뒤 아래 전체를 입력합니다.

```text
/goal

plans/PHASE_01_EXECUTION_PLAN.md와 plans/PHASE_01_FOUNDATION_BRIEF.md를 정확히 구현하라.

하나의 목표:
외부 API 없이 fixture 데이터로 실행되는 안전한 Foundation을 만들고, 모든 Phase 1 검증이 통과할 때 종료한다.

반드시 읽을 파일:
- AGENTS.md
- plans/PHASE_01_EXECUTION_PLAN.md
- plans/PHASE_01_FOUNDATION_BRIEF.md
- docs/02_ARCHITECTURE.md
- docs/04_DATA_CONTRACTS.md
- docs/09_ASSETSQUARE_INTERFACE_SPEC.md
- docs/10_SECURITY_AND_OPERATIONS.md
- docs/11_ACCEPTANCE_TESTS.md
- docs/13_UI_AND_DASHBOARD_SPEC.md
- STATUS.md
- DECISIONS.md
- KNOWN_ISSUES.md

절대 비범위:
- 토스증권 실제 API 호출
- OpenDART 실제 API 호출
- SEC 실제 API 호출
- 뉴스·매크로 실제 수집
- 계좌 조회
- 주문·자동매매
- OpenAI API
- 유료 API
- 실제 API 키

작업 규칙:
1. 체크포인트 단위로 구현하고 각 체크포인트 뒤 관련 테스트를 실행한다.
2. 진행상태를 짧게 기록한다.
3. 사양 충돌은 임의 해결하지 말고 DECISIONS.md에 PROPOSED로 기록한다.
4. 누락값을 0으로 바꾸지 않는다.
5. fixture를 실데이터로 표현하지 않는다.
6. 시크릿이 프론트엔드, 로그, Git에 없음을 검증한다.
7. Windows PowerShell에서 setup/dev/test가 가능하도록 한다.
8. 외부 네트워크가 없어도 전체 테스트가 통과해야 한다.
9. 실패 테스트를 skip 또는 삭제해 통과시키지 않는다.
10. 구현 결과는 멱등적이어야 한다.

완료 조건:
- Next.js/TypeScript 프론트엔드 실행
- FastAPI/Python 백엔드 실행
- /health 성공
- fixture 기반 Company 화면
- fixture 기반 Data Quality 화면
- 공통 데이터 계약 validation
- SQLite migration과 재실행
- fixture import 멱등성
- structured logging
- loading/empty/error 상태
- frontend lint/typecheck/test/build PASS
- backend lint/typecheck/unit/integration PASS
- migration test PASS
- idempotency test PASS
- secret scan PASS
- 실제 주문 관련 호출 경로 없음
- OpenAI API 의존성·호출 없음
- 외부 API 의존 없는 테스트
- qa/PHASE_01_SELF_QA.md 생성
- STATUS.md, CHANGELOG.md 갱신
- 미완료·한계는 KNOWN_ISSUES.md 갱신

완료 선언 전에 실제 검증 명령을 모두 실행하고 결과를 요약하라.

완료조건을 충족할 수 없다면 범위를 임의 축소하지 말고 상태를 PARTIAL 또는 BLOCKED로 보고하고, 원인·영향·다음 조치를 기록하라.
```
