# Project Status

- 프로젝트 상태: `PHASE 1 IMPLEMENTED — SELF-QA PASS`
- 현재 Phase: `Phase 1 — Fixture Foundation 완료, 독립 리뷰 대기`
- 현재 버전: `0.1.0`
- 구현 기준 commit: `f358fa3f0d1af44d0348bc5ba5c48be7866d7b21`
- 최종 QA일: `2026-08-22`
- 실제 API 연결: `아니오`
- 실제 주문 기능: `비활성 / 비범위`
- OpenAI API 사용: `아니오`
- Phase 2 상태: `미착수`

## 완료 상태

- [x] Phase 1 상세 실행계획 승인
- [x] 합성 fixture 기반 FastAPI/SQLite Foundation
- [x] 읽기 전용 Company/Data Quality UI
- [x] OpenAPI 계약과 생성 타입 drift 검사
- [x] Windows setup 2회 재현
- [x] 개발 서버 smoke와 소유 프로세스 정리
- [x] backend 172개, frontend 43개, E2E 2개
- [x] migration 왕복과 fixture import 멱등성
- [x] production build, secret scan, Phase 1 policy scan
- [x] Phase 1 자체 QA 문서와 증빙 보존
- [ ] 별도 Codex 작업의 독립 리뷰
- [ ] 사용자 최종 승인

## 승인 대기 항목

1. `prompts/02_PHASE_01_INDEPENDENT_REVIEW_PROMPT.md`로 구현 commit과 현재 QA diff를 독립 검토한다.
2. P0=0, P1=0과 P2 처리 여부를 확인한다.
3. 사용자 승인 전에는 `main` 병합, 버전 태그, GitHub Release를 수행하지 않는다.
4. Phase 2는 별도 착수 승인 전까지 시작하지 않는다.

## 알려진 운영 조건

- Node.js 지원 범위는 24.16 이상 25 미만이며 QA 기준은 24.19.0이다.
- ADR-009는 아직 `PROPOSED`이며 독립 리뷰·승인 대상이다.
- 모든 표시 데이터는 합성 fixture이고 실제 투자 판단 자료가 아니다.
- 실제 Toss/OpenDART/SEC/news/macro connector, 계좌와 주문은 구현하지 않았다.
