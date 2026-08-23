export function FixtureBanner() {
  return (
    <aside className="fixture-banner" aria-label="Fixture 데이터 안내" data-testid="fixture-banner">
      <strong className="fixture-banner__label">FIXTURE</strong>
      <span>합성 샘플 · 실제 투자 데이터 아님</span>
      <span className="fixture-banner__detail">계산 엔진이 아닌 Phase 1 화면 골격입니다.</span>
    </aside>
  );
}
