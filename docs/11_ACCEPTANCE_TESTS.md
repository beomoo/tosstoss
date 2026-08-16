# Acceptance Tests

## 1. 버그 우선순위

### P0
- 시크릿 노출
- 실제 주문 가능
- 데이터 원본 훼손
- 잘못된 종목 매핑으로 전면 오판
- 재무 단위 오류로 가격이 중대하게 왜곡
- 수정 공시를 원본과 중복 합산

### P1
- 핵심 기능 누락
- 계산 오류
- 기준일·제출일 혼동
- 13F 수량·평가액 오판
- 누락값 0 처리
- 중요 테스트 부재

### P2
- 일부 예외
- UI 설명 부족
- 운영 편의
- 비핵심 성능

---

## 2. 공통 Phase Gate

다음 Phase 진입 조건:

```text
P0 = 0
P1 = 0
P2 = 수정 또는 승인된 이월
필수 테스트 PASS
build PASS
secret scan PASS
QA 문서 완료
STATUS/CHANGELOG 갱신
```

---

## 3. Phase 0 승인 기준

- 문서 충돌 목록
- 누락 요구사항
- 지나친 범위
- Phase 1 파일 목록
- 테스트 명령
- 완료조건
- 비범위
- 위험과 롤백
- 코딩하지 않음

---

## 4. Phase 1 승인 기준

### 실행
- Windows 또는 현재 환경에서 setup 가능
- frontend와 backend 실행
- `/health` 성공
- fixture 화면 로드

### 구조
- 권장 계층 분리
- Pydantic 계약
- SQLite migration
- fixture import 멱등성
- 로그 구조화

### 보안
- 실제 키 없음
- 프론트엔드 시크릿 없음
- localhost
- 주문 코드 없음
- OpenAI API 없음

### 데이터
- SourceRecord
- SecurityMaster
- 샘플 가격
- 샘플 수급
- 샘플 재무
- 샘플 기관 보유
- DataQualityStatus
- null과 시간대 검증

### 테스트
- lint
- typecheck
- frontend unit
- backend unit
- integration
- migration
- idempotency
- secret scan
- build

### 산출물
- `qa/PHASE_01_SELF_QA.md`
- 샘플 JSON
- 실행 스크린샷 또는 Playwright 결과
- `STATUS.md`
- `CHANGELOG.md`

---

## 5. 후속 핵심 계약 테스트

### 토스
- 토큰 단일 관리자
- 인증 오류
- 호출 제한
- 잠정·확정
- stale
- 재수집 멱등성

### DART
- 연결·별도
- 단위
- 정정
- 철회
- 원문 링크
- 최신본과 전체 이력

### 13F
- 수량·평가액 분리
- HR/A
- NT
- Combination
- 중복 제거
- PUT/CALL
- 매핑 실패
- 기준일·제출일

### 가치평가
- 수동 계산 대조
- 음수 EPS
- 단위·통화
- 확률 100%
- reverse valuation

### 공시 비교
- 이동과 삭제 구분
- 숫자 diff
- 톤다운
- 원문 대조
- 오탐

---

## 6. QA 결과 형식

각 항목은 다음 중 하나:

```text
정상
실제 버그/구현 누락 — P0/P1/P2
기능 개선 권고
미확인
```

구현자의 설명보다 실제 코드, JSON, DB, 테스트 로그, 원문을 우선한다.
