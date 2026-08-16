import { redirect } from "next/navigation";

import { StatePanel } from "@/components/StatePanel";
import { getSecurities } from "@/lib/api.server";

export default async function HomePage() {
  let issuerId: string | undefined;
  try {
    const response = await getSecurities();
    issuerId = response.data[0]?.issuer_id;
  } catch {
    return (
      <StatePanel
        kind="error"
        title="Fixture 목록을 불러오지 못했습니다"
        message="로컬 FastAPI가 127.0.0.1에서 실행 중인지 확인한 뒤 다시 시도하세요."
      />
    );
  }

  if (issuerId === undefined) {
    return (
      <StatePanel
        kind="empty"
        title="표시할 합성 기업이 없습니다"
        message="API는 정상 응답했지만 Phase 1 security fixture 목록이 비어 있습니다."
      />
    );
  }

  redirect(`/company/${encodeURIComponent(issuerId)}`);
}
