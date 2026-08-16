# Data Contracts

## 1. 공통 규칙

- 내부 ID는 외부 티커와 분리한다.
- 시간은 timezone-aware UTC로 저장한다.
- 사용자 표시 기본 시간대는 `Asia/Seoul`.
- 금액·수량·비율은 `Decimal` 또는 DB의 정밀 numeric 표현을 사용한다.
- 결측은 `null`로 저장하고 `missing_reason`을 함께 둘 수 있다.
- 원문 ID와 정규화 레코드 ID를 연결한다.
- 계약 버전을 포함한다.

---

## 2. SourceRecord

```json
{
  "source_record_id": "src_...",
  "source_system": "OPENDART",
  "source_type": "FILING",
  "external_id": "receipt_or_accession",
  "source_locator": "official locator",
  "observed_at": "2026-06-30T00:00:00Z",
  "published_at": "2026-08-14T00:00:00Z",
  "fetched_at": "2026-08-16T09:00:00Z",
  "freshness_status": "FRESH",
  "finality_status": "FINAL",
  "revision_status": "ORIGINAL",
  "content_hash": "sha256",
  "parser_version": "0.1.0",
  "raw_storage_ref": "raw/..."
}
```

---

## 3. SecurityMaster

```json
{
  "security_id": "sec_...",
  "issuer_id": "issuer_...",
  "market": "KR",
  "exchange": "KOSPI",
  "ticker": "000000",
  "name": "샘플기업",
  "share_class": "COMMON",
  "currency": "KRW",
  "corp_code": null,
  "cik": null,
  "cusip": null,
  "isin": null,
  "figi": null,
  "mapping_status": "VERIFIED",
  "valid_from": null,
  "valid_to": null
}
```

---

## 4. PriceBar

```json
{
  "security_id": "sec_...",
  "interval": "1d",
  "bar_start": "2026-08-14T00:00:00Z",
  "open": "100.00",
  "high": "110.00",
  "low": "98.00",
  "close": "108.00",
  "volume": "1000000",
  "currency": "USD",
  "adjustment_status": "RAW",
  "source_record_id": "src_..."
}
```

복합 수정주가를 제공할 경우 원본 가격과 조정계수를 분리한다.

---

## 5. DailyMarketFlow

```json
{
  "security_id": "sec_...",
  "trade_date": "2026-08-14",
  "participant": "FOREIGN",
  "net_quantity": "120000",
  "net_value": "4500000000",
  "provisional": true,
  "source_record_id": "src_..."
}
```

---

## 6. FinancialFact

```json
{
  "issuer_id": "issuer_...",
  "report_type": "QUARTERLY",
  "fiscal_period": "2026Q2",
  "statement": "INCOME_STATEMENT",
  "account_code": "Revenue",
  "account_name_original": "매출액",
  "value": "100000000000",
  "currency": "KRW",
  "unit_scale": "1",
  "consolidation": "CONSOLIDATED",
  "period_start": "2026-04-01",
  "period_end": "2026-06-30",
  "source_record_id": "src_..."
}
```

---

## 7. FilingDocument

```json
{
  "filing_id": "filing_...",
  "issuer_id": "issuer_...",
  "jurisdiction": "KR",
  "form_type": "QUARTERLY_REPORT",
  "period_end": "2026-06-30",
  "filed_at": "2026-08-14T00:00:00Z",
  "revision_status": "ORIGINAL",
  "supersedes_filing_id": null,
  "source_record_id": "src_..."
}
```

---

## 8. FilingSentenceChange

```json
{
  "change_id": "chg_...",
  "issuer_id": "issuer_...",
  "previous_filing_id": "filing_prev",
  "current_filing_id": "filing_curr",
  "section_key": "BUSINESS_OVERVIEW",
  "change_type": "TONE_DOWN",
  "previous_sentence": "강력한 성장이 예상됩니다.",
  "current_sentence": "안정적인 성장이 가능할 것으로 예상됩니다.",
  "semantic_similarity": "0.84",
  "confidence": "0.91",
  "rule_hits": ["STRONG_TO_MODERATE", "CERTAINTY_REDUCED"],
  "review_status": "UNREVIEWED"
}
```

---

## 9. InstitutionManager

```json
{
  "manager_id": "mgr_...",
  "display_name": "Sample Manager",
  "legal_name": "Sample Manager LLC",
  "cik": "0000000000",
  "manager_type": "ACTIVE_ASSET_MANAGER",
  "parent_manager_id": null,
  "reporting_manager_id": "mgr_...",
  "reporting_structure": "DIRECT",
  "signal_weight": "1.00",
  "active_status": true
}
```

---

## 10. InstitutionHolding

```json
{
  "filing_id": "ifiling_...",
  "manager_id": "mgr_...",
  "security_id": "sec_...",
  "cusip_original": "000000000",
  "issuer_name_original": "SAMPLE INC",
  "title_of_class": "COM",
  "put_call": null,
  "shares": "1000000",
  "market_value_reported": "250000000",
  "portfolio_weight": "0.025",
  "mapping_status": "VERIFIED",
  "source_record_id": "src_..."
}
```

---

## 11. InstitutionHoldingChange

```json
{
  "manager_id": "mgr_...",
  "security_id": "sec_...",
  "previous_period": "2026-03-31",
  "current_period": "2026-06-30",
  "previous_shares": "800000",
  "current_shares": "1000000",
  "shares_delta": "200000",
  "shares_delta_pct": "0.25",
  "weight_delta": "0.004",
  "rank_delta": "-12",
  "change_class": "ADD",
  "estimated_trade_effect": null,
  "confidence": "0.90",
  "limitations": ["ACTUAL_TRADE_DATE_UNKNOWN"]
}
```

---

## 12. ValuationScenario

```json
{
  "valuation_run_id": "val_...",
  "issuer_id": "issuer_...",
  "scenario": "BASE",
  "as_of": "2026-08-16",
  "method": "PER",
  "forecast_eps": "12000",
  "target_multiple": "17",
  "implied_price": "204000",
  "probability": "0.55",
  "assumption_source": "USER",
  "formula_version": "per_v1",
  "input_data_ids": ["fact_...", "price_..."]
}
```

---

## 13. Evidence

```json
{
  "evidence_id": "ev_...",
  "issuer_id": "issuer_...",
  "evidence_type": "DIRECT_SOURCE",
  "direction": "SUPPORTING",
  "claim": "북미 수주잔고가 증가했다.",
  "source_record_id": "src_...",
  "source_excerpt": "원문 일부",
  "observed_at": "2026-06-30T00:00:00Z",
  "confidence": "1.00"
}
```

---

## 14. Hypothesis

Phase 1에서는 테이블을 반드시 구현할 필요는 없지만 계약과 확장 위치를 깨지 않도록 한다.

```json
{
  "hypothesis_id": "hyp_...",
  "issuer_id": "issuer_...",
  "title": "북미 데이터센터 전력 인프라 수요 확대",
  "status": "STRENGTHENING",
  "time_horizon": "6_18_MONTHS",
  "supporting_evidence_ids": [],
  "contradicting_evidence_ids": [],
  "invalidation_condition_ids": [],
  "created_at": "2026-08-16T00:00:00Z",
  "updated_at": "2026-08-16T00:00:00Z"
}
```

---

## 15. DataQualityStatus

```json
{
  "source_system": "SEC_EDGAR",
  "dataset": "13F",
  "last_success_at": "2026-08-16T08:30:00Z",
  "last_observed_at": "2026-06-30T00:00:00Z",
  "freshness_status": "FRESH",
  "finality_status": "FINAL",
  "error_code": null,
  "error_message": null,
  "records_received": 100,
  "records_rejected": 2,
  "quality_flags": ["UNRESOLVED_CUSIP"]
}
```

---

## 16. 계약 테스트

각 계약에 대해 최소한 다음을 테스트한다.

- 필수 필드
- timezone
- Decimal 정밀도
- enum
- null 처리
- 원문 ID 추적
- 직렬화 왕복
- 버전 호환
