import { StatePanel } from "@/components/StatePanel";

export default function Loading() {
  return (
    <StatePanel
      kind="loading"
      title="합성 fixture를 불러오는 중입니다"
      message="기준시각과 데이터 상태를 함께 확인하고 있습니다."
    />
  );
}
