# Security and Operations

## 1. 보안 목표

- 증권사 시크릿과 계좌정보 보호
- 브라우저·Git·로그 노출 방지
- 주문 기능 차단
- 데이터 손상 방지
- 로컬 복구 가능성
- 분석과 실제 거래 분리

---

## 2. 기본 환경값

```text
LOCAL_ONLY=true
TRADING_ENABLED=false
DRY_RUN=true
OPENAI_API_ENABLED=false
ALLOW_ACCOUNT_ENDPOINTS=false
```

코드 기본값도 안전한 값이어야 한다. 환경변수 누락 시 위험 기능이 켜지면 안 된다.

---

## 3. 시크릿

- `.env`는 Git 제외
- `.env.example`에는 키 이름만
- 서버 프로세스만 접근
- UI 응답에 포함 금지
- 로그 마스킹
- 예외 traceback에 헤더·토큰 금지
- 테스트 fixture에 실제 값 금지
- secret scan을 CI 또는 로컬 검사에 포함

---

## 4. 네트워크

- 현재 runtime은 `127.0.0.1` 바인딩
- 현재 및 별도 승인되지 않은 작업의 LAN·공개 인터넷 노출 금지
- CORS는 로컬 프론트엔드만 허용
- 토스 API는 백엔드에서만 호출
- 허용 IP와 호출 한도는 공식 설정 사용
- TLS 검증 해제 금지

미래 `Public Read-only Deployment`는 별도 체크포인트와 명시적 승인 후에만 인터넷 도달성을 도입할 수 있다. 그 예외는 approved public-safe projection의 읽기 전용 API/UI에만 적용되며 owner/admin, 내부 DB, source admission, task control, 시크릿, 계좌·증권사 자격증명과 trading surface에는 적용되지 않는다. 현재 CORS, 바인딩과 `LOCAL_ONLY=true`를 미리 완화하지 않는다.

---

## 5. 주문 차단

현재 저장소에는 주문 실행 코드를 만들지 않는다.

향후 별도 프로젝트에서도 다음이 필요하다.

- 별도 서비스
- 명시적 사용자 승인
- 포지션 한도
- 일 손실 한도
- 중복 주문 방지
- kill switch
- 주문 전 최신 잔고
- 데이터 지연 시 차단
- 감사 로그

이 항목은 현재 구현의 근거가 아니라 미래 승인 체크리스트다.

미래 자동매매에서 AI/Codex는 broker authority가 아닌 untrusted order-intent producer다. Deterministic risk policy engine을 우회하거나 자신의 위험 한도를 변경할 수 없고, 제한된 trade executor만 broker API에 접근해야 한다. Trading enable, 금액 한도 상향, 허용 종목 확대, 제한 완화와 kill-switch 복구는 강한 인간 권한이 필요하다.

---

## 6. 신뢰 도메인과 침해 격리

- `PUBLIC`: 익명 사용자가 approved public-safe 분석 출력만 읽는다.
- `OWNER / ADMIN`: 강한 인간 인증으로 privileged mutation과 승인을 수행한다.
- `TRADING`: 미래의 인간 승인 위험 한도 안에서 deterministic execution만 수행한다.

세 도메인은 같은 인증·권한 모델로 합치지 않는다. Public surface 침해가 owner/admin 또는 trading 권한, 내부 저장소, 시크릿이나 직접 실행 경로를 자동으로 제공하지 않아야 한다. 이 장기 격리 요구는 아직 구현됐다고 주장하지 않는다.

---

## 7. 데이터 보호

- 원문은 append-only 또는 버전 보존
- 정정본이 원본 파일을 물리적으로 덮어쓰지 않음
- DB 마이그레이션 전 백업
- 삭제 작업은 dry-run과 범위 확인
- 자동 정리 정책은 사용자 승인 전 금지

---

## 8. 로그

로그에 포함:
- 작업 ID
- 데이터 소스
- 단계
- 레코드 수
- 상태
- 지연
- 오류 코드

로그에서 제외:
- API 키
- Authorization 헤더
- 전체 계좌번호
- 개인정보
- 전체 원문 응답의 무조건적 출력

---

## 9. 백업

읽기 전용 v1.0 이전 최소 요구:
- SQLite 백업
- Parquet 디렉터리 백업
- 설정과 스키마 버전
- 복원 테스트
- 백업 성공·실패 상태

---

## 10. 로컬 실행

Windows 우선 스크립트 후보:

```text
scripts/setup.ps1
scripts/dev.ps1
scripts/test.ps1
scripts/backup.ps1
scripts/restore-test.ps1
```

Phase 1에서는 setup, dev, test의 최소 경로를 만든다.

---

## 11. 보안 완료 기준

- 실제 키 없음
- Git 추적 없음
- 브라우저 번들 없음
- 로그 없음
- 위험 기능 기본 OFF
- localhost 바인딩
- secret scan PASS
- 테스트가 위험 설정을 검증
