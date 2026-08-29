# Project Instructions for Codex

## 1. 프로젝트 목적

토스증권 Open API, OpenDART, SEC EDGAR 등 공식·합법적 데이터 소스를 이용해 현재는 개인용 로컬 **읽기 전용 기업분석 웹 대시보드**를 구축한다.

장기 제품 방향에는 별도 승인된 공개 읽기 전용 대시보드와 별도 승인된 자동매매 프로젝트가 포함될 수 있다. 이는 현재 구현·배포·거래 권한이 아니며 `PUBLIC`, `OWNER / ADMIN`, `TRADING`은 서로 다른 신뢰 도메인으로 유지한다.

현재 저장소는 단계별 구현 방식으로 운영한다. 전체 사양을 참고하되, 현재 Phase의 명시적 범위를 넘어 구현하지 않는다.

---

## 2. 작업 전 필수 확인

모든 작업 시작 전에 다음을 읽는다.

1. `README_START_HERE.md`
2. `docs/00_MASTER_IMPLEMENTATION_PLAN.md`
3. 현재 작업에 해당하는 `plans/PHASE_XX_*.md`
4. 현재 작업과 직접 관련된 상세 사양서
5. `docs/10_SECURITY_AND_OPERATIONS.md`
6. `docs/11_ACCEPTANCE_TESTS.md`
7. `STATUS.md`
8. `DECISIONS.md`
9. `KNOWN_ISSUES.md`

문서 간 충돌이 있으면 임의로 선택하지 않는다. 충돌 위치와 영향을 `DECISIONS.md`에 `PROPOSED` 상태로 기록하고, 안전하고 되돌릴 수 있는 범위만 진행한다.

---

## 3. 절대 조건

- 현재 승인된 작업에서는 실제 주문 기능을 구현하거나 활성화하지 않는다.
- `TRADING_ENABLED=false`, `DRY_RUN=true`, `LOCAL_ONLY=true`를 기본 원칙으로 유지한다.
- OpenAI API를 호출하지 않는다.
- 유료 데이터 API를 추가하지 않는다.
- 토스 Client Secret, Access Token, DART 키 등 시크릿을 프론트엔드, Git, 로그, 테스트 fixture, 화면에 포함하지 않는다.
- 브라우저에서 증권사 API를 직접 호출하지 않는다.
- 누락·실패·미확인 데이터를 `0`, 빈 문자열, 임의 추정값으로 대체하지 않는다.
- `source`, `observed_at`, `published_at`, `fetched_at`, `freshness_status`, `finality_status`, `revision_status`를 가능한 범위에서 보존한다.
- 금액·주식 수·EPS 등 정밀 계산에 binary float를 사용하지 않는다.
- 저장 시각은 UTC를 원칙으로 하고 화면 표시는 `Asia/Seoul`을 기본으로 한다.
- 외부 API의 응답 구조나 엔드포인트를 추측하여 구현하지 않는다. 구현 시점의 공식 문서를 확인한다.
- 테스트 실패를 삭제, skip, xfail 또는 조건부 우회로 숨기지 않는다.
- mock/fixture 구현을 실제 연동 완료로 표현하지 않는다.
- 사양과 완료 기준을 Codex가 임의로 낮추지 않는다.
- 데이터 원문과 시스템 추론을 구분한다.

현재 및 별도 승인되지 않은 모든 작업은 `LOCAL_ONLY=true`를 유지한다. 공개 네트워크 노출은 미래의 명시적인 `Public Read-only Deployment` 체크포인트에서만 검토할 수 있고, 그 승인은 승인된 public-safe 읽기 전용 출력에만 적용된다. `OWNER / ADMIN`, 내부 저장소, 시크릿, 증권사 자격증명과 `TRADING`의 인터넷 노출 또는 권한을 함께 승인하지 않는다. 현재 승인 범위에서는 `TRADING_ENABLED=false`와 `DRY_RUN=true`가 필수다.

---

## 4. 구현 원칙

- 작은 변경 단위와 검증 가능한 체크포인트를 사용한다.
- 외부 API 커넥터, 정규화, 저장, 분석, UI를 분리한다.
- 커넥터 원문 응답과 정규화 결과를 추적 가능하게 연결한다.
- 모든 수집 작업은 멱등성을 가져야 한다.
- 수정 공시, 재수집, 중복 이벤트를 고려한다.
- 분석 결과에는 사용한 입력 데이터 버전과 계산식 버전을 남긴다.
- UI는 최신값만 보여주는 대신 기준일과 수집일을 함께 보여준다.
- 오류 시 전체 서비스가 멈추는 대신 해당 데이터 소스의 상태를 `ERROR`, `STALE`, `UNAVAILABLE`로 표시한다.
- 실제 코드와 테스트가 없는 TODO를 완료로 간주하지 않는다.

---

## 5. 권장 저장소 구조

```text
apps/web/                 Next.js + TypeScript
services/api/             FastAPI + Python
services/api/connectors/  외부 데이터 소스 커넥터
services/api/domain/      도메인 모델과 규칙
services/api/storage/     DB·Parquet 저장 계층
services/api/jobs/        수집·재계산 작업
services/api/routes/      REST API
tests/                    단위·계약·통합 테스트
fixtures/                 비식별·비밀정보 없는 샘플 데이터
scripts/                  실행·검증 스크립트
docs/
plans/
qa/
prompts/
```

구조 변경이 필요하면 이유와 마이그레이션 영향을 `DECISIONS.md`에 먼저 기록한다.

---

## 6. 완료 전 필수 검증

현재 Phase에 맞는 다음 명령을 실제로 실행한다.

- frontend lint
- frontend typecheck
- frontend test
- frontend build
- backend lint/format check
- backend typecheck
- backend unit test
- backend integration test
- DB migration test
- fixture import idempotency test
- secret scan
- Phase별 acceptance test

명령이 아직 정의되지 않은 Phase에서는 실행 가능한 표준 스크립트를 먼저 만든다.

---

## 7. 완료 보고 형식

각 Phase 종료 시 다음을 제출한다.

1. 변경 파일 목록
2. 구현된 요구사항
3. 구현하지 않은 요구사항
4. 실행한 명령과 결과
5. 생성한 샘플 JSON 또는 화면
6. 보안 확인 결과
7. 알려진 제한사항
8. 잔여 위험
9. `qa/PHASE_XX_SELF_QA.md`
10. 갱신된 `STATUS.md`, `CHANGELOG.md`, 필요 시 `KNOWN_ISSUES.md`

완료 조건을 충족하지 못하면 `완료`라고 선언하지 않는다.
