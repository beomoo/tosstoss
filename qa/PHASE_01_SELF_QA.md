# Phase 01 Self QA

## 1. 판정

- 결과: `PASS`
- 구현 기준 commit: `f358fa3f0d1af44d0348bc5ba5c48be7866d7b21`
- QA snapshot: 위 commit과 본 문서·증빙·scan digest 수정 diff
- 검토일: `2026-08-22`
- 검토자: `Codex 자체 QA`
- 범위: 외부 API가 없는 합성 fixture 기반 로컬 읽기 전용 Foundation
- 결함 집계: `P0 0개 / P1 0개 / P2 0개`

## 2. 실행 환경과 방식

- Windows 11 build 26200, PowerShell 7.6.4, Python 3.13.1
- 공식 portable Node.js 24.19.0, npm 11.17.0
- Node ZIP SHA-256: `57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73`
- 시스템 Node.js와 전역 npm은 변경하지 않았다.
- 기존 최종 통합 로그를 먼저 회수했으며, 이미 통과한 테스트를 다시 실행하지 않았다.
- 통합 실행의 마지막 실패였던 stale lock digest만 수정하고 `secret-scan.ps1`과 `policy-scan.ps1`을 최종 snapshot에서 별도로 실행했다.

## 3. 테스트 결과

| 명령/게이트 | 결과 | 증거와 비고 |
|---|---|---|
| `scripts/setup.ps1` 2회 | PASS | 두 실행 모두 478 packages 설치, 외부 API 자격증명 요구 없음 |
| `scripts/dev.ps1 -Smoke` | PASS | Web/API 정상, JSON 로그 14줄, 종료 후 3000/8000 listener와 관련 프로세스 0개 |
| 상속 `NODE_OPTIONS` negative canary | PASS | Node 작업 전에 fail-closed 거부 |
| Ruff format/check와 ESLint | PASS | 67 files formatted, Ruff 오류 0, ESLint warning 0 |
| mypy와 TypeScript | PASS | mypy 40 source files, Next route typegen과 `tsc --noEmit` 통과 |
| process cleanup canary | PASS | 20회, 자식 제거·무관 프로세스 보존·owner crash kill-on-close 확인 |
| backend pytest | PASS | 172/172 |
| migration | PASS | 반복 upgrade, disposable downgrade, re-upgrade |
| fixture import idempotency | PASS | 2차 `inserted=0`, `updated=0`, `unchanged=13`; PK/row count/canonical digest 동일 |
| frontend Vitest | PASS | 10 files, 43/43 |
| OpenAPI drift | PASS | snapshot과 생성 TypeScript 일치 |
| Next.js production build | PASS | 통합 실행과 E2E 전 build 모두 성공 |
| Playwright Chromium | PASS | 2/2, 합성 화면·모든 issuer·안전한 not-found |
| `scripts/secret-scan.ps1` | PASS | stale 승인 digest 수정 뒤 최종 staged snapshot 검사 |
| `scripts/policy-scan.ps1` | PASS | Phase 1 범위, exact inventory와 59개 control-plane digest 검사 |

통합 `scripts/test.ps1`은 기능·계약·빌드·E2E까지 모두 통과한 뒤, 마지막 secret scan의 stale `package-lock.json` 승인 digest에서 exit 1이었다. 잠금 파일 내용은 정상이며 `npm ci` 2회와 policy scan의 독립 lock digest가 이미 검증했다. 사용자 요청에 따라 전체 통합 실행은 반복하지 않았고, 승인 digest와 제어 파일 digest를 동기화한 뒤 실패한 secret/policy 게이트만 별도로 PASS시켜 최종 판정을 구성했다.

## 4. 증빙 파일

| 파일 | 내용 | SHA-256 |
|---|---|---|
| `qa/evidence/phase_01/setup.txt` | 최종 setup 2회 | `e2a4ee2194889156af2a18dce594c258958fa2b5938726a6b7a92cec50327962` |
| `qa/evidence/phase_01/dev-smoke.txt` | 최종 개발 서버 smoke | `3d838aecb5d033b02b2bc032a4929b39f31be8b3208fc8123468283a3cb847f4` |
| `qa/evidence/phase_01/test.txt` | 최종 통합 실행과 원래 stale digest 실패 | `5e3df7e7a0c47226a8e4b9f43163f9bde34268eb7e6f59b70aaf50fc3785870f` |
| `qa/evidence/phase_01/company.png` | 최종 Company 화면 | `d048aee09293b90a990e984b95c0aeffac3870a17502a9b6b7fece3174168d06` |
| `qa/evidence/phase_01/data-quality.png` | 최종 Data Quality 화면 | `f5e7722b3b95606b8cf354da06fc8bf67943104c011f713d475b7acf879a96ce` |
| `qa/evidence/phase_01/sample-analysis-packet.json` | 합성 analysis packet | `5478228cd2cf628cada4ba3d909a9ef3049e227193875dbefdc1fe94eb753978` |
| `qa/evidence/phase_01/sample-company-overview.json` | 합성 company overview | `1c0e22d1ee62ac1e5b87f30d43f608e46e81540914bfa35966bb27cb8f56eb55` |
| `qa/evidence/phase_01/sample-data-quality.json` | 합성 data quality | `456c3c51dd4ac324de1b2372a2159fe47cb05b9f04d6beed3ade039bb17dada5` |
| `qa/evidence/phase_01/sample-health.json` | health response | `aebe563184b982a0b7eb18b29a0e71f42dcfd36cb5fe3d34f27b8d7276b9b796` |

`migration.txt`와 `import-fixtures.txt`는 개별 실행 보조 로그이며, 구현 기준 commit의 최종 migration/import 결과는 `test.txt`에 포함돼 있다.

## 5. 정상 확인 항목

- strict Pydantic, UTC Z, Decimal string, 구조화 null 사유와 revision/source 추적
- 합성 KR/US issuer와 AVAILABLE/DEGRADED/ERROR/UNAVAILABLE 데이터 품질 상태
- loading/empty/error/not-found의 결정적 UI
- localhost 전용 바인딩, 정확한 host/CORS allowlist와 non-loopback 차단
- request ID와 구조화 로그, traceback·환경변수·Authorization 비노출
- 읽기 전용 경계와 주문·계좌·외부 connector·OpenAI 코드 부재
- package/requirements lock, 테스트 inventory와 제어 파일 digest 고정

## 6. 알려진 제한

- 모든 데이터와 화면은 합성 fixture이며 실제 투자 데이터나 계산 엔진 결과가 아니다.
- Toss/OpenDART/SEC/news/macro, 계좌, 주문, 자동매매, OpenAI API는 Phase 1 비범위다.
- npm 11.17.0은 `esbuild`와 `unrs-resolver` install script 승인 대기 경고를 출력했으나 설치, typecheck, 두 production build와 E2E는 정상 통과했다. 자동 승인은 수행하지 않았다.
- Node.js 24.15 이하 Windows 네이티브 TCP 충돌은 최소 버전 제한으로 완화했으며 ADR-009는 아직 `PROPOSED`다.
- 전체 `scripts/test.ps1`을 수정 후 재실행하지 않았으므로 최종 PASS는 기존 통합 로그와 별도 secret/policy PASS의 합성 증거다.
- 별도 Codex 작업의 독립 리뷰와 사용자 승인은 아직 수행하지 않았다.

## 7. 다음 승인 게이트

- [x] P0=0
- [x] P1=0
- [x] P2=0
- [x] Phase 1 기능·계약·빌드·보안·정책 게이트 PASS
- [x] 상태·변경이력·자체 QA와 증빙 갱신
- [ ] 별도 독립 리뷰
- [ ] 사용자 승인
- [ ] 승인 후에만 `main` 병합·태그·GitHub Release 검토

Phase 2는 시작하지 않는다.
