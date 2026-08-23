import Link from "next/link";
import type { ReactNode } from "react";

import { BackendStatus, type BackendConnectionState } from "@/components/BackendStatus";
import { FixtureBanner } from "@/components/FixtureBanner";

interface AppShellProps {
  backendState: BackendConnectionState;
  children: ReactNode;
}

const futureNavigation = ["Market", "Smart Money", "Filings & Events", "Valuation Lab", "Settings"];

export function AppShell({ backendState, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        본문으로 건너뛰기
      </a>
      <FixtureBanner />
      <header className="app-header">
        <div>
          <p className="eyebrow">LOCAL RESEARCH WORKSPACE</p>
          <Link className="brand" href="/" aria-label="기업분석 대시보드 홈">
            기업분석 대시보드
          </Link>
        </div>
        <BackendStatus state={backendState} />
      </header>
      <div className="shell-grid">
        <aside className="sidebar">
          <nav aria-label="주요 메뉴">
            <p className="nav-label">Phase 1</p>
            <Link className="nav-item nav-item--enabled" href="/">
              Company
            </Link>
            <Link className="nav-item nav-item--enabled" href="/data-quality">
              Data Quality
            </Link>
            <p className="nav-label nav-label--future">Future phases</p>
            {futureNavigation.map((label) => (
              <button
                className="nav-item nav-item--disabled"
                type="button"
                disabled
                aria-label={`${label}, 후속 Phase에서 제공`}
                key={label}
              >
                <span>{label}</span>
                <span className="nav-item__phase">예정</span>
              </button>
            ))}
          </nav>
          <div className="scope-note">
            <strong>읽기 전용</strong>
            <span>외부 API 연결 없음</span>
          </div>
        </aside>
        <main id="main-content" className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
