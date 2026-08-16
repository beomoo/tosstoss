import { DataField } from "@/components/DataField";
import { DataQualityGrid } from "@/components/DataQualityGrid";
import { StatusBadge } from "@/components/StatusBadge";
import {
  formatDateOnly,
  formatDecimal,
  formatMissingReason,
  formatTimestamp,
} from "@/lib/format";
import type {
  CompanyOverview as CompanyOverviewData,
  DailyMarketFlow,
  Evidence,
  FilingSentenceChange,
  FinancialFact,
  InstitutionHoldingChange,
  InstitutionManager,
  PriceBar,
  ValuationScenario,
} from "@/types/api.contract";

interface CompanyOverviewProps {
  overview: CompanyOverviewData;
}

const participantLabels: Record<DailyMarketFlow["participant"], string> = {
  INDIVIDUAL: "개인",
  FOREIGN: "외국인",
  INSTITUTION: "기관",
};

function SectionEmpty({ children }: { children: string }) {
  return <p className="section-empty">{children}</p>;
}

function FinancialFacts({ facts }: { facts: FinancialFact[] }) {
  if (facts.length === 0) {
    return <SectionEmpty>표시할 합성 재무 fact가 없습니다.</SectionEmpty>;
  }
  return (
    <div className="metric-grid">
      {facts.map((fact) => (
        <article className="metric-card" key={fact.financial_fact_id}>
          <div className="card-heading-row">
            <p className="metric-card__label">{fact.account_name_original}</p>
            <StatusBadge status={fact.finality_status} label="확정 상태" />
          </div>
          <p className="metric-card__value">
            {fact.value === null
              ? `확인 불가 — ${formatMissingReason(fact.missing_reasons?.value)}`
              : formatDecimal(fact.value, fact.currency)}
          </p>
          <p className="metric-card__meta">
            {fact.fiscal_period} · {formatDateOnly(fact.period_start)} ~ {formatDateOnly(fact.period_end)}
          </p>
        </article>
      ))}
    </div>
  );
}

function MarketFlows({ flows, currency }: { flows: DailyMarketFlow[]; currency: string }) {
  if (flows.length === 0) {
    return <SectionEmpty>이 종목에는 국내 단기 수급 샘플이 없습니다.</SectionEmpty>;
  }
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">합성 국내 단기 수급</caption>
        <thead>
          <tr>
            <th scope="col">참여자</th>
            <th scope="col">순수량</th>
            <th scope="col">순금액</th>
            <th scope="col">상태</th>
          </tr>
        </thead>
        <tbody>
          {flows.map((flow) => (
            <tr key={flow.market_flow_id}>
              <th scope="row">{participantLabels[flow.participant]}</th>
              <td>
                {flow.net_quantity === null
                  ? `확인 불가 — ${formatMissingReason(flow.missing_reasons?.net_quantity)}`
                  : formatDecimal(flow.net_quantity, "주")}
              </td>
              <td>
                {flow.net_value === null
                  ? `확인 불가 — ${formatMissingReason(flow.missing_reasons?.net_value)}`
                  : formatDecimal(flow.net_value, currency)}
              </td>
              <td>
                <StatusBadge status={flow.finality_status} label="확정 상태" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ValuationCards({ scenarios }: { scenarios: ValuationScenario[] }) {
  if (scenarios.length === 0) {
    return <SectionEmpty>정적 가치평가 샘플이 없습니다. Phase 1에는 계산 엔진이 없습니다.</SectionEmpty>;
  }
  return (
    <div className="scenario-grid">
      {scenarios.map((scenario) => (
        <article className="scenario-card" key={scenario.valuation_scenario_id}>
          <div className="card-heading-row">
            <h3>{scenario.scenario}</h3>
            <span className="sample-result">SAMPLE_RESULT</span>
          </div>
          <p className="scenario-card__price">{formatDecimal(scenario.implied_price, scenario.currency)}</p>
          <dl className="compact-list">
            <DataField label="확률" value={formatDecimal(scenario.probability)} note="Decimal string" />
            <DataField label="예상 EPS" value={formatDecimal(scenario.forecast_eps, scenario.currency)} />
            <DataField label="목표 배수" value={formatDecimal(scenario.target_multiple, "x")} />
            <DataField label="단위 배율" value={formatDecimal(scenario.unit_scale)} />
            <DataField label="가정 출처" value={scenario.assumption_source} />
            <DataField label="기준일" value={formatDateOnly(scenario.as_of)} />
          </dl>
        </article>
      ))}
    </div>
  );
}

function InstitutionChanges({
  changes,
  managers,
}: {
  changes: InstitutionHoldingChange[];
  managers: InstitutionManager[];
}) {
  if (changes.length === 0) {
    return <SectionEmpty>표시할 합성 기관 보유 변화가 없습니다.</SectionEmpty>;
  }
  return (
    <div className="stack-list">
      {changes.map((change) => (
        <article className="line-card" key={change.holding_change_id}>
          <div>
            <span className="sample-result">SAMPLE_RESULT</span>
            <h3>{managers.find((manager) => manager.manager_id === change.manager_id)?.display_name ?? change.manager_id}</h3>
            <p>
              {formatDateOnly(change.previous_period)} → {formatDateOnly(change.current_period)}
            </p>
          </div>
          <dl className="compact-list compact-list--inline">
            <DataField label="변화 구분" value={change.change_class} />
            <DataField
              label="주식 수 변화"
              value={formatDecimal(change.shares_delta, "주")}
            />
            <DataField label="확신도" value={formatDecimal(change.confidence)} />
          </dl>
          {change.limitations.length === 0 ? null : (
            <p className="limitation">제한: {change.limitations.join(", ")}</p>
          )}
        </article>
      ))}
    </div>
  );
}

function FilingChanges({ changes }: { changes: FilingSentenceChange[] }) {
  if (changes.length === 0) {
    return <SectionEmpty>정적 공시 문구 변화 샘플이 없습니다.</SectionEmpty>;
  }
  return (
    <div className="stack-list">
      {changes.map((change) => (
        <article className="filing-card" key={change.change_id}>
          <div className="card-heading-row">
            <div>
              <span className="sample-result">SAMPLE_RESULT</span>
              <h3>{change.section_key}</h3>
            </div>
            <div className="tag-list" aria-label="변화 태그">
              {change.change_types.map((type) => (
                <span key={type}>{type}</span>
              ))}
            </div>
          </div>
          <div className="sentence-comparison">
            <div>
              <p className="sentence-label">이전 합성 문장</p>
              <p>{change.previous_sentence}</p>
            </div>
            <div>
              <p className="sentence-label">현재 합성 문장</p>
              <p>{change.current_sentence}</p>
            </div>
          </div>
          <p className="review-note">
            {change.human_review_required ? "사람 검토 필요" : "사람 검토 불필요"} · {change.review_status} · 확신도 {formatDecimal(change.confidence)}
          </p>
        </article>
      ))}
    </div>
  );
}

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) {
    return <SectionEmpty>표시할 근거 샘플이 없습니다.</SectionEmpty>;
  }
  return (
    <div className="stack-list">
      {evidence.map((item) => {
        return (
          <article className="evidence-card" key={item.evidence_id}>
            <div className="card-heading-row">
              <span className="evidence-basis">{item.evidence_basis}</span>
              <span className="verification-status">{item.verification_status}</span>
            </div>
            <p className="evidence-card__claim">{item.claim}</p>
            <p className="evidence-card__excerpt">{item.source_excerpt ?? "원문 발췌 확인 불가"}</p>
            <div className="evidence-card__meta">
              <span>{formatTimestamp(item.observed_at)}</span>
              <span>원문 레코드: {item.source_record_id ?? "확인 불가"}</span>
            </div>
          </article>
        );
      })}
    </div>
  );
}

export function CompanyOverview({ overview }: CompanyOverviewProps) {
  const { issuer, security } = overview;
  const priceBars = overview.price_bars ?? [];
  const valuationScenarios = overview.valuation_scenarios ?? [];
  const financialFacts = overview.financial_facts ?? [];
  const marketFlows = overview.market_flows ?? [];
  const institutionHoldingChanges = overview.institution_holding_changes ?? [];
  const institutionManagers = overview.institution_managers ?? [];
  const filingSentenceChanges = overview.filing_sentence_changes ?? [];
  const evidence = overview.evidence ?? [];
  const dataQuality = overview.data_quality ?? [];
  const latestPrice = priceBars.reduce<PriceBar | null>(
    (latest, item) => (latest === null || item.bar_start > latest.bar_start ? item : latest),
    null,
  );

  return (
    <div className="page-stack">
      <header className="company-hero">
        <div>
          <p className="eyebrow">SYNTHETIC COMPANY FIXTURE</p>
          <h1>{issuer.display_name}</h1>
          <p className="company-hero__legal">{issuer.legal_name}</p>
        </div>
        <div className="security-chip" aria-label="선택된 합성 증권">
          <strong>{security.ticker}</strong>
          <span>{security.exchange}</span>
          <span>{security.currency}</span>
        </div>
      </header>

      <section className="notice-card" aria-label="샘플 결과 안내">
        <span className="sample-result">SAMPLE_RESULT</span>
        <p>아래 수치와 문장은 계약과 화면 상태를 검증하기 위한 합성 fixture이며 실제 분석 결과가 아닙니다.</p>
      </section>

      <section className="dashboard-section" aria-labelledby="price-heading">
        <div className="section-heading">
          <div>
            <p className="section-index">01</p>
            <h2 id="price-heading">최근 가격 샘플</h2>
          </div>
          {latestPrice === null ? null : (
            <div className="badge-row">
              <StatusBadge status={latestPrice.finality_status} label="확정 상태" />
              <StatusBadge status={latestPrice.revision_status} label="정정 상태" />
            </div>
          )}
        </div>
        {latestPrice === null ? (
          <dl className="compact-list">
            <DataField
              label="종가"
              value={null}
              missingReason={overview.missing_reasons?.["price_bars"]}
            />
          </dl>
        ) : (
          <div className="price-panel">
            <div>
              <span>합성 종가</span>
              <strong>{formatDecimal(latestPrice.close, latestPrice.currency)}</strong>
            </div>
            <dl className="price-details">
              <DataField label="거래일" value={formatDateOnly(latestPrice.exchange_trade_date)} />
              <DataField label="기준시각" value={formatTimestamp(latestPrice.bar_start)} />
              <DataField label="시가" value={formatDecimal(latestPrice.open, latestPrice.currency)} />
              <DataField label="고가" value={formatDecimal(latestPrice.high, latestPrice.currency)} />
              <DataField label="저가" value={formatDecimal(latestPrice.low, latestPrice.currency)} />
              <DataField label="거래량" value={formatDecimal(latestPrice.volume, "주")} />
            </dl>
          </div>
        )}
      </section>

      <section className="dashboard-section" aria-labelledby="valuation-heading">
        <div className="section-heading">
          <div>
            <p className="section-index">02</p>
            <h2 id="valuation-heading">가치평가 시나리오 골격</h2>
          </div>
          <p>PER 정적 샘플 · 계산 엔진 아님</p>
        </div>
        <ValuationCards scenarios={valuationScenarios} />
      </section>

      <section className="dashboard-section" aria-labelledby="financial-heading">
        <div className="section-heading">
          <div>
            <p className="section-index">03</p>
            <h2 id="financial-heading">재무 fact</h2>
          </div>
          <p>기간과 확정 상태를 분리 표시</p>
        </div>
        <FinancialFacts facts={financialFacts} />
      </section>

      <section className="dashboard-section" aria-labelledby="flow-heading">
        <div className="section-heading">
          <div>
            <p className="section-index">04</p>
            <h2 id="flow-heading">국내 단기 수급</h2>
          </div>
          <p>null은 0으로 표시하지 않음</p>
        </div>
        <MarketFlows flows={marketFlows} currency={security.currency} />
      </section>

      <section className="dashboard-section" aria-labelledby="institution-heading">
        <div className="section-heading">
          <div>
            <p className="section-index">05</p>
            <h2 id="institution-heading">기관 보유 변화</h2>
          </div>
          <p>보고기간 기준 정적 샘플</p>
        </div>
        <InstitutionChanges
          changes={institutionHoldingChanges}
          managers={institutionManagers}
        />
      </section>

      <section className="dashboard-section" aria-labelledby="filing-heading">
        <div className="section-heading">
          <div>
            <p className="section-index">06</p>
            <h2 id="filing-heading">공시 문구 변화</h2>
          </div>
          <p>복수 변화 태그와 사람 검토 상태</p>
        </div>
        <FilingChanges changes={filingSentenceChanges} />
      </section>

      <section className="dashboard-section" aria-labelledby="evidence-heading">
        <div className="section-heading">
          <div>
            <p className="section-index">07</p>
            <h2 id="evidence-heading">근거와 확인 상태</h2>
          </div>
          <p>원문·계산·구조적 추론을 분리</p>
        </div>
        <EvidenceList evidence={evidence} />
      </section>

      <section className="dashboard-section" aria-labelledby="quality-heading">
        <div className="section-heading">
          <div>
            <p className="section-index">08</p>
            <h2 id="quality-heading">데이터 품질</h2>
          </div>
          <p>오류가 있어도 마지막 정상 상태를 보존</p>
        </div>
        {dataQuality.length === 0 ? (
          <SectionEmpty>표시할 소스 품질 상태가 없습니다.</SectionEmpty>
        ) : (
          <DataQualityGrid statuses={dataQuality} />
        )}
      </section>
    </div>
  );
}
