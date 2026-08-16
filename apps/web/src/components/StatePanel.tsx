import type { ReactNode } from "react";

type StateKind = "loading" | "empty" | "error" | "not-found";

interface StatePanelProps {
  kind: StateKind;
  title: string;
  message: string;
  action?: ReactNode;
}

const stateIcons: Record<StateKind, string> = {
  loading: "···",
  empty: "○",
  error: "!",
  "not-found": "?",
};

export function StatePanel({ kind, title, message, action }: StatePanelProps) {
  const alertProps = kind === "error" ? { role: "alert" as const } : { role: "status" as const };

  return (
    <section className="state-panel" data-state={kind} aria-live={kind === "loading" ? "polite" : "off"} {...alertProps}>
      <span className="state-panel__icon" aria-hidden="true">
        {stateIcons[kind]}
      </span>
      <div>
        <h1>{title}</h1>
        <p>{message}</p>
        {action === undefined ? null : <div className="state-panel__action">{action}</div>}
      </div>
    </section>
  );
}
