"use client";

import { StatePanel } from "@/components/StatePanel";

export default function CompanyError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <StatePanel
      kind="error"
      title="기업 fixture를 표시하지 못했습니다"
      message="다른 소스의 상태는 보존됩니다. 로컬 API를 확인한 뒤 이 카드 묶음만 다시 요청하세요."
      action={
        <button className="button" type="button" onClick={reset}>
          기업 화면 다시 시도
        </button>
      }
    />
  );
}
