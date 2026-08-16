import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import type { BackendConnectionState } from "@/components/BackendStatus";
import { getHealth } from "@/lib/api.server";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Fixture 기업분석 대시보드",
    template: "%s · Fixture 기업분석 대시보드",
  },
  description: "외부 API 없이 합성 fixture로 동작하는 읽기 전용 Phase 1 대시보드",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

async function getBackendState(): Promise<BackendConnectionState> {
  try {
    await getHealth();
    return "ONLINE";
  } catch {
    return "OFFLINE";
  }
}

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const backendState = await getBackendState();

  return (
    <html lang="ko" data-scroll-behavior="smooth">
      <body>
        <AppShell backendState={backendState}>{children}</AppShell>
      </body>
    </html>
  );
}
