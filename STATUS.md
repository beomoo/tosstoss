# Project Status

- 프로젝트 상태: `PHASE 2 IMPLEMENTATION IN PROGRESS — CP2-A/CP2-B/CP2-C PASS`
- 현재 Phase: `Phase 2 — bounded rate/retry 완료 / CP2-D 미착수`
- 현재 버전: `0.1.0`
- Phase 1 최종 검증 commit: `57b2a63ead06d03191d8094e1689b8d2ab3d7764`
- Phase 1 PR: `#1`
- Phase 1 merge commit: `b1829a7375704271a21267e1fcf62808147be593`
- Release baseline tag: `v0.1.0`
- 최종 QA일: `2026-08-23 (CP2-C P2 cumulative-wait hardening)`
- 실제 API 연결: `아니오`
- 실제 주문 기능: `비활성 / 비범위`
- OpenAI API 사용: `아니오`
- Phase 2 상태: `CP2-A PASS / CP2-B PASS / CP2-B P2 hardening PASS / CP2-C PASS / CP2-D NOT STARTED`

## 완료 상태

- [x] Phase 1 상세 실행계획 승인
- [x] 합성 fixture 기반 FastAPI/SQLite Foundation
- [x] 읽기 전용 Company/Data Quality UI
- [x] OpenAPI 계약과 생성 타입 drift 검사
- [x] Windows setup 2회 재현
- [x] 개발 서버 smoke와 소유 프로세스 정리
- [x] backend 251개, frontend 43개, E2E 2개
- [x] migration 왕복과 fixture import 멱등성
- [x] production build, secret scan, Phase 1 policy scan
- [x] Phase 1 자체 QA 문서와 증빙 보존
- [x] 별도 Codex 작업의 독립 리뷰 PASS
- [x] 사용자 최종 승인과 PR #1 병합
- [x] Phase 1 완료 태그 `v0.1.0`
- [x] Phase 2 CP1 공식 계약 조사와 실행계획
- [x] Phase 2 CP2-A Toss-only connector namespace·dependency·credential config 경계
- [x] Phase 2 CP2-A origin/endpoint/import/account/order/secret negative canary
- [x] CP2-A 전체 회귀: backend 176개, frontend 43개, E2E 2개, build·secret·policy PASS
- [x] Phase 2 CP2-B strict OAuth response와 process-owned memory-only token manager
- [x] Phase 2 CP2-B 100-coroutine single-flight, monotonic expiry, generation-aware invalidation
- [x] Phase 2 CP2-B exact origin·method/path·header/query boundary와 401 1회 replay
- [x] CP2-B 전체 회귀: backend 251개, frontend 43개, E2E 2개, build·secret·policy PASS
- [x] Phase 2 CP2-B P2 hardening: public token manager/lease/raw bearer surface 제거, backend 252개
- [x] Phase 2 CP2-C client×group shared limiter와 7개 callable group exact mapping
- [x] Phase 2 CP2-C strict rate header telemetry, bounded 429/5xx retry와 safe typed exhaustion/deferred error
- [x] Phase 2 CP2-C concurrency·cancellation·401/OAuth 429 interaction offline 검증
- [x] CP2-C 독립 검토 P2 수정: 429 이후 Reset acquire wait와 backoff를 operation별 누적 30초 예산으로 통합
- [x] CP2-C P2 수정 전체 회귀: backend 321개, frontend 43개, E2E 2개, build·secret·policy PASS

## Phase 1 종료 기준

```text
Phase 1: COMPLETE
Independent QA: PASS
PR: #1
Merge commit: b1829a7375704271a21267e1fcf62808147be593
Release baseline tag: v0.1.0
```

Phase 2 구현은 진행 중이다. CP2-A 보안 경계, CP2-B OAuth/token manager/exact HTTP client와 P2 hardening, CP2-C rate limiter/retry/error taxonomy를 완료했다. 모든 connector 검증은 합성 credential, `httpx.MockTransport`, fake clock/sleeper/jitter만 사용했으며 실제 token·시장 API 요청은 하지 않았다. CP2-D live preflight는 시작하지 않는다.

## 알려진 운영 조건

- Node.js 지원 범위는 24.16 이상 25 미만이며 QA 기준은 24.19.0이다.
- ADR-009는 아직 `PROPOSED`이며 독립 리뷰·승인 대상이다.
- 모든 표시 데이터는 합성 fixture이고 실제 투자 판단 자료가 아니다.
- 실제 Toss/OpenDART/SEC/news/macro connector, 계좌와 주문은 구현하지 않았다.
- Toss connector는 application-owned shared client와 client×rate-group limiter 구조로 구현됐지만 실제 credential 사용, 실제 rate header와 live API timing 검증은 아직 없다.
