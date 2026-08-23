# Phase 01 Self QA

## 1. 판정

- 결과: `PASS`
- 최종 통합 검증 기준: `18c5f464ed3bf9ea7a41596760f16636b04454e4` + 본 커밋의 policy scope 보강
- QA snapshot: 위 기준에서 실행한 전체 통합 테스트와 본 문서·최종 `test.txt` 갱신 diff
- 검토일: `2026-08-23`
- 검토자: `Codex 자체 QA`
- 범위: 외부 API가 없는 합성 fixture 기반 로컬 읽기 전용 Foundation
- 결함 집계: `P0 0개 / P1 0개 / P2 0개`
- 종료 상태: 독립 검증 `PASS`, PR `#1`, merge commit `b1829a7375704271a21267e1fcf62808147be593`, tag `v0.1.0`

## 2. 실행 환경과 방식

- Windows 11 build 26200, PowerShell 7.6.4, Python 3.13.1
- 공식 portable Node.js 24.19.0, npm 11.17.0
- Node ZIP SHA-256: `57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73`
- 시스템 Node.js와 전역 npm은 변경하지 않았다.
- 최종 검증 commit에서 `scripts/setup.ps1`을 2회 실행해 모두 exit 0을 확인했다.
- 이어서 `scripts/test.ps1` 전체를 한 번의 연속 실행으로 재실행해 exit 0과 마지막 `All Phase 1 checks passed.`를 확인했다.

## 3. 테스트 결과

| 명령/게이트 | 결과 | 증거와 비고 |
|---|---|---|
| `scripts/setup.ps1` 2회 | PASS | 두 실행 모두 478 packages 설치, 외부 API 자격증명 요구 없음 |
| `scripts/dev.ps1 -Smoke` | PASS | Web/API 정상, JSON 로그 14줄, 종료 후 3000/8000 listener와 관련 프로세스 0개 |
| 상속 `NODE_OPTIONS` negative canary | PASS | Node 작업 전에 fail-closed 거부 |
| 미승인 최상위 source directory negative canary | PASS | `connectors/`, `broker/`, `phase2/`, `experimental/`의 주문/OpenAI/외부 connector 코드 거부 |
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
| `scripts/test.ps1` | PASS | 한 번의 연속 실행, exit 0, 마지막 `All Phase 1 checks passed.` 확인 |
| 통합 실행 내부 secret scan | PASS | `Secret scan passed.` 확인 |
| 통합 실행 내부 policy scan | PASS | `Phase 1 scope policy scan passed.` 확인 |

최종 snapshot에서 `scripts/test.ps1` 전체를 재실행해 exit 0 및 `All Phase 1 checks passed.`를 확인했다. backend, frontend, migration, fixture idempotency, OpenAPI drift, production build, E2E, secret scan과 policy scan이 동일 프로세스 체인의 한 번의 연속 실행 안에서 모두 통과했다.

정책 변경 직후 첫 전체 실행에서는 external connector canary의 의도적인 외부 URL 리터럴이 정책 스크립트 자체의 기존 URL 검사에 잡혔다. canary 문자열을 기존 self-test와 같은 분할 조합 방식으로 수정한 뒤 전체 테스트를 처음부터 다시 실행했다. 최종 증빙 실행은 모든 출력 스트림을 보존한 별도의 연속 실행이며 부분 테스트 결과를 사용하지 않았다.

## 4. 증빙 파일

| 파일 | 내용 | SHA-256 |
|---|---|---|
| `qa/evidence/phase_01/setup.txt` | 최종 setup 2회 | `e2a4ee2194889156af2a18dce594c258958fa2b5938726a6b7a92cec50327962` |
| `qa/evidence/phase_01/dev-smoke.txt` | 최종 개발 서버 smoke | `3d838aecb5d033b02b2bc032a4929b39f31be8b3208fc8123468283a3cb847f4` |
| `qa/evidence/phase_01/test.txt` | P2 보강 후 최종 snapshot 전체 통합 실행 PASS | `6d7f391ec4e8171b2df6bfc7adb7e7c438c140f03acc18ebb6ef8b138aed9f32` |
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
- 독립 검증 P2였던 새 최상위 source directory의 policy-scan 우회 가능성은 exact allowlist와 negative canary로 해소했다. 이후 독립 검증 PASS와 사용자 최종 승인을 거쳐 PR #1이 병합됐다.

## 7. 다음 승인 게이트

- [x] P0=0
- [x] P1=0
- [x] P2=0
- [x] Phase 1 기능·계약·빌드·보안·정책 게이트 PASS
- [x] 상태·변경이력·자체 QA와 증빙 갱신
- [x] 별도 독립 리뷰 PASS
- [x] 사용자 승인
- [x] PR #1 `main` 병합과 `v0.1.0` 태그 생성
- [ ] GitHub Release는 생성하지 않음

Phase 2는 시작하지 않는다.
