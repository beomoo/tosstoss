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

- 초기에는 `127.0.0.1` 바인딩
- LAN·공개 인터넷 노출 금지
- CORS는 로컬 프론트엔드만 허용
- 토스 API는 백엔드에서만 호출
- 허용 IP와 호출 한도는 공식 설정 사용
- TLS 검증 해제 금지

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

---

## 6. 데이터 보호

- 원문은 append-only 또는 버전 보존
- 정정본이 원본 파일을 물리적으로 덮어쓰지 않음
- DB 마이그레이션 전 백업
- 삭제 작업은 dry-run과 범위 확인
- 자동 정리 정책은 사용자 승인 전 금지

---

## 7. 로그

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

## 8. 백업

읽기 전용 v1.0 이전 최소 요구:
- SQLite 백업
- Parquet 디렉터리 백업
- 설정과 스키마 버전
- 복원 테스트
- 백업 성공·실패 상태

---

## 9. 로컬 실행

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

## 10. 보안 완료 기준

- 실제 키 없음
- Git 추적 없음
- 브라우저 번들 없음
- 로그 없음
- 위험 기능 기본 OFF
- localhost 바인딩
- secret scan PASS
- 테스트가 위험 설정을 검증
