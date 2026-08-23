# Project Status

- 프로젝트 상태: `PHASE 1 COMPLETE — INDEPENDENT QA PASS`
- 현재 Phase: `Phase 2 — 토스증권 읽기 전용 데이터 계획 준비`
- 현재 버전: `0.1.0`
- Phase 1 최종 검증 commit: `57b2a63ead06d03191d8094e1689b8d2ab3d7764`
- Phase 1 PR: `#1`
- Phase 1 merge commit: `b1829a7375704271a21267e1fcf62808147be593`
- Release baseline tag: `v0.1.0`
- 최종 QA일: `2026-08-23`
- 실제 API 연결: `아니오`
- 실제 주문 기능: `비활성 / 비범위`
- OpenAI API 사용: `아니오`
- Phase 2 상태: `브랜치 준비 단계 / 구현 미착수`

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
- [x] 별도 Codex 작업의 독립 리뷰 PASS
- [x] 사용자 최종 승인과 PR #1 병합
- [x] Phase 1 완료 태그 `v0.1.0`

## Phase 1 종료 기준

```text
Phase 1: COMPLETE
Independent QA: PASS
PR: #1
Merge commit: b1829a7375704271a21267e1fcf62808147be593
Release baseline tag: v0.1.0
```

Phase 2 코드는 아직 시작하지 않는다. 전용 실행계획을 작성·검토하고 별도 구현 승인을 받은 뒤 착수한다.

## 알려진 운영 조건

- Node.js 지원 범위는 24.16 이상 25 미만이며 QA 기준은 24.19.0이다.
- ADR-009는 아직 `PROPOSED`이며 독립 리뷰·승인 대상이다.
- 모든 표시 데이터는 합성 fixture이고 실제 투자 판단 자료가 아니다.
- 실제 Toss/OpenDART/SEC/news/macro connector, 계좌와 주문은 구현하지 않았다.
