# Project Status

- 프로젝트 상태: `PHASE 2 IMPLEMENTATION IN PROGRESS — CP2 COMPLETE / CP3-A IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW / CP3-B NOT STARTED`
- 현재 Phase: `Phase 2 — CP3-A Security Master + Current Price documentation/contract checkpoint`
- 현재 버전: `0.1.0`
- Phase 1 최종 검증 commit: `57b2a63ead06d03191d8094e1689b8d2ab3d7764`
- Phase 1 PR: `#1`
- Phase 1 merge commit: `b1829a7375704271a21267e1fcf62808147be593`
- Release baseline tag: `v0.1.0`
- 최종 QA일: `2026-08-24 (CP3-A documentation + full offline regression)`
- 실제 API 연결: `CP2-D2 one-shot PASS — OAuth + GET /api/v1/stocks만 검증`
- 실제 주문 기능: `비활성 / 비범위`
- OpenAI API 사용: `아니오`
- Phase 2 상태: `CP1 PASS / CP2 COMPLETE / CP3-A IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW / CP3-B NOT STARTED`

## 완료 상태

- [x] Phase 1 상세 실행계획 승인
- [x] 합성 fixture 기반 FastAPI/SQLite Foundation
- [x] 읽기 전용 Company/Data Quality UI
- [x] OpenAPI 계약과 생성 타입 drift 검사
- [x] Windows setup 2회 재현
- [x] 개발 서버 smoke와 소유 프로세스 정리
- [x] backend 357개, frontend 43개, E2E 2개
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
- [x] CP2-D1 three-way opt-in, runtime contract drift gate, one-shot OAuth/stocks preflight tooling
- [x] CP2-D1 MockTransport·SelfTest·redaction 검증과 전체 회귀: backend 357개, frontend 43개, E2E 2개, build·secret·policy PASS
- [x] CP2-D2 actual OAuth와 `GET /api/v1/stocks` one-shot PASS, allowed-IP 실행 경로와 성공 응답 Limit/Remaining/Reset header 검증
- [x] Vitest stdout/stderr 분리, strict UTF-8 byte-safe JSON array와 한국어 test name을 포함한 exact 43 inventory gate
- [x] CP2 final integrated QA: P0 0 / P1 0 / unresolved functional P2 0 / deferred environment P2 1
- [x] CP3-A Security Master + Current Price 계획·계약 문서 작성
- [x] ADR-011 nullable source-time proposal 수정 및 ADR-012 provider staging identity proposal 추가
- [x] CP3-A application/test/fixture/migration/dependency/runtime/API route 변경 0
- [ ] CP3-A GPT independent review 및 사용자 승인
- [ ] CP3-B Contract Foundation + additive migration 시작 승인

## Phase 1 종료 기준

```text
Phase 1: COMPLETE
Independent QA: PASS
PR: #1
Merge commit: b1829a7375704271a21267e1fcf62808147be593
Release baseline tag: v0.1.0
```

Phase 2 구현은 계속 진행 중이며 CP2만 `COMPLETE`다. CP2-A 보안 경계, CP2-B OAuth/token manager/exact HTTP client와 token-boundary hardening, CP2-C rate limiter/retry/error taxonomy와 cumulative-wait hardening, CP2-D1 safe preflight offline validation, CP2-D2 actual one-shot을 final integrated QA로 닫았다. 사용자 독립 실행의 safe fixed summary에서 provider contract drift 없음, OpenAPI `3.1.0`, provider version `1.2.14`, actual OAuth와 `GET /api/v1/stocks` 성공, allowed-IP 실행 경로와 성공 응답의 Limit/Remaining/Reset header 유효성을 확인했다. credential 값, token, body와 raw header 값은 기록하지 않았다.

CP3-A에서는 Security Master와 Current Price의 endpoint 역할, KR/US universe, provider staging identity, lifecycle, nullable source time, PriceSnapshot, raw/source/hash/idempotency, additive migration/rollback과 CP3-B/C/D acceptance를 문서화했다. ADR-011은 revised `PROPOSED`, ADR-012는 신규 `PROPOSED`이며 어느 결정도 Codex가 승인하지 않았다. application code, test, fixture, migration, dependency, runtime config, API route와 connector implementation은 변경하지 않았다. CP3-A 상태는 `IMPLEMENTED — AWAITING GPT INDEPENDENT REVIEW`이고 CP3-B는 시작하지 않았다.

`[LIVE_VERIFIED]` 범위는 canonical provider contract, actual OAuth token issuance와 credential acceptance, allowed-IP 실행 경로, actual `GET /api/v1/stocks` 구조, 성공 응답의 Limit/Remaining/Reset header다. natural 429 `Retry-After`, actual 429/5xx, production retry timing, 나머지 Phase 2 market endpoint, CP3 이후 데이터 semantics/freshness는 계속 `[LIVE_UNVERIFIED]`다. Phase 2 전체 완료나 CP3 시작을 의미하지 않는다.

## 알려진 운영 조건

- Node.js 지원 범위는 24.16 이상 25 미만이며 QA 기준은 24.19.0이다.
- ADR-009는 아직 `PROPOSED`이며 독립 리뷰·승인 대상이다.
- 모든 표시 데이터는 합성 fixture이고 실제 투자 판단 자료가 아니다.
- Toss market connector는 CP2 범위에서 구현됐지만 실제 데이터 수집·정규화·저장·화면 연결은 CP3-B 이후 별도 승인 범위다. CP3-A에서는 문서만 변경했다. OpenDART/SEC/news/macro, 계좌와 주문은 구현하지 않았다.
- Windows 개발·QA 저장소는 현재 ASCII-only parent path를 사용한다. non-ASCII parent path의 setuptools editable build 실패는 `P2 DEFERRED / ENVIRONMENT CONSTRAINT`이며 CP2 business logic 결함으로 분류하지 않는다.
