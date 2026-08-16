# Phase 1 구현 후 별도 Codex 채팅에 입력할 독립 리뷰 프롬프트

구현에 사용한 채팅과 **다른 Codex 채팅**을 열고 아래를 입력합니다.

```text
/review

현재 Phase 1 브랜치를 구현자의 설명을 신뢰하지 말고 독립적으로 검토하라.

검토 전 읽을 파일:
- AGENTS.md
- plans/PHASE_01_EXECUTION_PLAN.md
- plans/PHASE_01_FOUNDATION_BRIEF.md
- docs/02_ARCHITECTURE.md
- docs/04_DATA_CONTRACTS.md
- docs/09_ASSETSQUARE_INTERFACE_SPEC.md
- docs/10_SECURITY_AND_OPERATIONS.md
- docs/11_ACCEPTANCE_TESTS.md
- qa/PHASE_01_SELF_QA.md
- STATUS.md
- KNOWN_ISSUES.md

이번 리뷰에서는 코드를 수정하지 않는다.

검토 항목:
1. 요구사항 누락
2. 구현 범위 초과
3. 시크릿 노출
4. 주문·OpenAI·외부 API의 숨은 경로
5. null을 0이나 빈 문자열로 바꾸는 코드
6. timezone과 Decimal 오류
7. migration 비멱등성
8. fixture import 중복
9. mock을 실데이터로 표현
10. 테스트가 통과해도 실제 요구는 충족하지 않는 경우
11. 실패 테스트의 skip, xfail, 삭제
12. frontend/backend 계약 불일치
13. 구조화 로그의 민감정보
14. Windows 실행 재현성
15. 문서와 코드 차이
16. 유지보수·확장성을 막는 하드코딩

가능하면 실제 명령을 실행하고 결과를 확인한다.

결과를 qa/PHASE_01_INDEPENDENT_REVIEW.md 형식으로 작성하라.

각 항목 분류:
- 정상
- 실제 버그/구현 누락: P0/P1/P2
- 기능 개선 권고
- 미확인

모든 문제는 파일 경로, 줄 또는 재현 명령, 기대 결과, 실제 결과, 수정 방향을 포함한다.

마지막에 Phase 2 진입 가능 여부를 PASS / CONDITIONAL PASS / FAIL로 판정한다.
```
