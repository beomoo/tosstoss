# Phase 1 Foundation Brief

## 1. 목적

실제 외부 API 없이 전체 시스템의 안전한 기반, 데이터 계약, 저장 구조, 테스트 체계, fixture 화면을 구축한다.

---

## 2. 포함 범위

### Backend
- FastAPI 앱
- `/health`
- `/api/v1/system/status`
- fixture 기반 기업 overview
- fixture 기반 data quality
- fixture 기반 analysis packet sample
- Pydantic 계약
- SQLite와 마이그레이션
- repository 인터페이스
- 구조화 로그
- 오류 처리

### Frontend
- Next.js + TypeScript
- 기본 레이아웃
- Company fixture 화면
- Data Quality fixture 화면
- backend health 상태
- loading, empty, error 상태

### Tooling
- setup
- dev
- test
- lint
- typecheck
- build
- secret scan
- fixture import
- Windows PowerShell 실행 경로

### Documentation
- 실행 방법
- 테스트 명령
- 구조
- Phase 1 QA

---

## 3. 비범위

- 토스 API
- DART API
- SEC API
- 뉴스
- 매크로
- 실제 가치평가 엔진
- 실제 공시 diff
- 실제 13F 파서
- 계좌 조회
- 주문
- OpenAI API
- 유료 API

fixture는 실제 기능을 가장하지 않아야 한다.

---

## 4. fixture 요구

최소:

- 국내 기업 1개
- 미국 기업 1개
- 가격 바
- 국내 단기 수급
- 재무 fact
- 기관 보유와 변화
- 공시 문장 변화 예시
- 가치평가 시나리오 예시
- 데이터 품질 정상·지연·오류 상태
- null 값
- 정정 상태

fixture에는 실제 API 키·개인정보가 없어야 한다.

---

## 5. 기술 결정 후보

Codex는 Phase 0 계획에서 다음을 구체화한다.

- 패키지 관리자
- Python 환경 관리자
- migration 도구
- 테스트 프레임워크
- 스크립트 명령
- monorepo 실행 방식
- 최소 지원 버전

선택은 무료이고 Windows에서 재현 가능해야 한다.

---

## 6. 완료 기준

1. 신규 환경 setup 문서
2. frontend/backend 실행
3. fixture 화면
4. DB migration
5. import 멱등성
6. 계약 validation
7. 모든 테스트
8. build
9. secret scan
10. 주문·OpenAI·외부 API 없음
11. QA·상태·변경 이력
12. 알려진 문제 기록
