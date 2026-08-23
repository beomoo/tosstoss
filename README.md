# Toss Invest Research Dashboard

로컬 Windows에서 실행되는 읽기 전용 기업분석 대시보드의 Phase 1 Foundation입니다.

현재 데이터는 모두 합성 fixture입니다. 실제 시세·공시·기관 보유가 아니며 투자 판단에 사용하면 안 됩니다. 실제 외부 API, 계좌 조회, 주문, OpenAI API 호출은 구현되어 있지 않습니다.

## 요구 환경

- Windows
- PowerShell 7.4 이상
- Node.js 24.16 이상 25 미만 (`.node-version`: 24.19.0)
- npm 11
- Python 3.13

경로에 공백이나 한글이 있어도 scripts 폴더의 명령은 저장소 루트를 자동으로 찾습니다.

## 최초 설정

의존성과 Playwright Chromium 설치를 위해 최초 한 번은 인터넷 연결이 필요합니다.

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
~~~

## 실행

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
~~~

- Web: http://127.0.0.1:3000
- API health: http://127.0.0.1:8000/health

두 서버는 127.0.0.1에만 바인딩됩니다. dev 스크립트를 종료하면 자신이 시작한 프로세스만 정리합니다.

## 전체 검증

setup 완료 후 다음 명령은 package를 설치하거나 외부 데이터 API를 호출하지 않습니다.

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1
~~~

개별 검증:

~~~powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\lint.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\typecheck.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\migrate.ps1 -Action Test
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\import-fixtures.ps1 -VerifyIdempotency
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\secret-scan.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\policy-scan.ps1
~~~

## 안전 원칙

- LOCAL_ONLY=true
- TRADING_ENABLED=false
- DRY_RUN=true
- OPENAI_API_ENABLED=false
- ALLOW_ACCOUNT_ENDPOINTS=false

위 값의 반대 설정은 Phase 1 애플리케이션 시작을 실패시킵니다. 실제 키는 저장소, fixture, 화면, 로그에 넣지 않습니다.

상세 사양은 README_START_HERE.md와 plans/PHASE_01_EXECUTION_PLAN.md를 참고하십시오.
