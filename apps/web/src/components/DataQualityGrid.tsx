import { DataField } from "@/components/DataField";
import { StatePanel } from "@/components/StatePanel";
import { StatusBadge } from "@/components/StatusBadge";
import { formatRecordCount, formatTimestamp } from "@/lib/format";
import { toSafeHttpsUrl } from "@/lib/safe-url";
import type { DataQualityStatus } from "@/types/api.contract";

interface DataQualityGridProps {
  statuses: DataQualityStatus[];
}

export function DataQualityGrid({ statuses }: DataQualityGridProps) {
  if (statuses.length === 0) {
    return (
      <StatePanel
        kind="empty"
        title="데이터 품질 항목이 없습니다"
        message="합성 fixture는 정상적으로 응답했지만 표시할 소스 상태가 없습니다."
      />
    );
  }

  return (
    <div className="quality-grid">
      {statuses.map((status) => {
        const safeUrl = toSafeHttpsUrl(status.source_locator);
        return (
          <article className="quality-card" key={status.quality_status_id}>
            <header>
              <div>
                <p className="eyebrow">{status.source_system}</p>
                <h2>{status.dataset}</h2>
              </div>
              <StatusBadge status={status.availability_status} label="가용성" />
            </header>

            <div className="quality-card__axes" aria-label="독립 상태 축">
              <StatusBadge status={status.freshness_status} label="신선도" />
              <StatusBadge status={status.finality_status} label="확정 상태" />
              <StatusBadge status={status.revision_status} label="정정 상태" />
            </div>

            <dl className="compact-list quality-card__details">
              <DataField
                label="마지막 시도"
                value={formatTimestamp(status.last_attempt_at)}
              />
              <DataField
                label="마지막 성공"
                value={status.last_success_at === null ? null : formatTimestamp(status.last_success_at)}
                missingReason={status.missing_reasons?.last_success_at}
              />
              <DataField
                label="데이터 기준시각"
                value={status.last_observed_at === null ? null : formatTimestamp(status.last_observed_at)}
                missingReason={status.missing_reasons?.last_observed_at}
              />
              <DataField label="신선도 평가시각" value={formatTimestamp(status.freshness_evaluated_at)} />
              <DataField label="수신 레코드" value={formatRecordCount(status.records_received)} />
              <DataField label="거부 레코드" value={formatRecordCount(status.records_rejected)} />
            </dl>

            {status.error_code === null ? (
              <p className="quality-card__message">보고된 소스 오류 없음</p>
            ) : (
              <div className="quality-card__error" role="status">
                <strong>{status.error_code}</strong>
                <span>{status.error_message ?? "상세 오류는 안전을 위해 제공되지 않음"}</span>
                {status.last_success_at === null ? null : (
                  <span>마지막 정상 데이터는 보존됨: {formatTimestamp(status.last_success_at)}</span>
                )}
              </div>
            )}

            {status.quality_flags.length === 0 ? null : (
              <div className="tag-list" aria-label="품질 플래그">
                {status.quality_flags.map((flag) => (
                  <span key={flag}>{flag}</span>
                ))}
              </div>
            )}

            <footer>
              {safeUrl === null ? (
                <span>출처: {status.source_locator ?? "확인 불가"}</span>
              ) : (
                <a href={safeUrl} target="_blank" rel="noreferrer noopener">
                  HTTPS 원문 열기
                </a>
              )}
            </footer>
          </article>
        );
      })}
    </div>
  );
}
