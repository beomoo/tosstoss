import { StatePanel } from "@/components/StatePanel";

export default function CompanyLoading() {
  return (
    <StatePanel
      kind="loading"
      title="기업 fixture를 불러오는 중입니다"
      message="가격, 재무, 수급, 공시와 데이터 품질 계약을 확인하고 있습니다."
    />
  );
}
