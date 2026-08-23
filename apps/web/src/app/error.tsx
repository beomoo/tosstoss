"use client";

import { StatePanel } from "@/components/StatePanel";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <StatePanel
      kind="error"
      title="화면을 안전하게 표시하지 못했습니다"
      message="오류 상세와 서버 설정은 화면에 노출하지 않았습니다. 로컬 서버 상태를 확인해 주세요."
      action={
        <button className="button" type="button" onClick={reset}>
          다시 시도
        </button>
      }
    />
  );
}
