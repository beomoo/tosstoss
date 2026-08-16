import type { Metadata } from "next";

import { DataQualityGrid } from "@/components/DataQualityGrid";
import { StatePanel } from "@/components/StatePanel";
import { getCompanyDataQuality, getSecurities } from "@/lib/api.server";

export const metadata: Metadata = { title: "Data Quality" };

export default async function DataQualityPage() {
  const securities = await getSecurities();
  const issuerSecurities = [
    ...new Map(securities.data.map((security) => [security.issuer_id, security])).values(),
  ];

  if (issuerSecurities.length === 0) {
    return (
      <StatePanel
        kind="empty"
        title="확인할 합성 기업이 없습니다"
        message="Data Quality는 issuer별 상태를 보여주므로 먼저 fixture security가 필요합니다."
      />
    );
  }

  const issuerResults = await Promise.all(
    issuerSecurities.map(async (security) => {
      try {
        return {
          state: "ready" as const,
          security,
          response: await getCompanyDataQuality(security.issuer_id),
        };
      } catch {
        return { state: "error" as const, security };
      }
    }),
  );

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">SOURCE HEALTH · FIXED EVALUATION TIME</p>
          <h1>Data Quality</h1>
          <p>가용성, 신선도, 확정, 정정 상태를 서로 섞지 않고 표시합니다.</p>
        </div>
        <div className="security-chip">
          <span>읽기 전용 fixture</span>
          <strong>전체 issuer {issuerResults.length}개</strong>
        </div>
      </header>
      <div className="quality-issuer-list">
        {issuerResults.map((result) => (
          <section
            className="quality-issuer"
            data-testid={`quality-issuer-${result.security.issuer_id}`}
            key={result.security.issuer_id}
            aria-labelledby={`quality-heading-${result.security.issuer_id}`}
          >
            <header className="quality-issuer__header">
              <div>
                <p className="eyebrow">
                  {result.security.market} · {result.security.exchange}
                </p>
                <h2 id={`quality-heading-${result.security.issuer_id}`}>
                  {result.security.issuer_id}
                </h2>
              </div>
              <div className="quality-issuer__security" aria-label="대표 security">
                <strong>{result.security.ticker}</strong>
                <span>{result.security.security_id}</span>
              </div>
            </header>
            {result.state === "ready" ? (
              <DataQualityGrid statuses={result.response.data} />
            ) : (
              <div className="quality-issuer__error" role="alert">
                이 issuer의 fixture 품질 상태를 불러오지 못했습니다. 다른 issuer 결과는 그대로
                유지됩니다.
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
