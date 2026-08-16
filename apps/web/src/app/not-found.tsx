import Link from "next/link";

import { StatePanel } from "@/components/StatePanel";

export default function NotFound() {
  return (
    <StatePanel
      kind="not-found"
      title="합성 기업을 찾을 수 없습니다"
      message="등록되지 않은 issuer ID입니다. Phase 1 fixture 목록에서 다시 선택하세요."
      action={
        <Link className="button" href="/">
          Fixture 홈으로
        </Link>
      }
    />
  );
}
