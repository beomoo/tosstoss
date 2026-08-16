export type BackendConnectionState = "ONLINE" | "DEGRADED" | "OFFLINE";

interface BackendStatusProps {
  state: BackendConnectionState;
}

const stateLabels: Record<BackendConnectionState, string> = {
  ONLINE: "Backend 정상",
  DEGRADED: "Backend 일부 제한",
  OFFLINE: "Backend 연결 불가",
};

export function BackendStatus({ state }: BackendStatusProps) {
  return (
    <div className="backend-status" data-state={state.toLowerCase()} aria-label={`서버 상태: ${stateLabels[state]}`}>
      <span className="backend-status__marker" aria-hidden="true" />
      <span>{stateLabels[state]}</span>
    </div>
  );
}
