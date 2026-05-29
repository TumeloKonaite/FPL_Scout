import { PageShell } from "@/components/PageShell";

export default function TransfersPage() {
  return (
    <PageShell
      title="Transfers"
      description="Evaluate transfer targets, sells, holds, and longer-term squad structure."
    >
      <section className="placeholder-grid" aria-label="Transfer placeholders">
        <div className="placeholder-card">
          <h2>Buy List</h2>
          <p>Collect recommended transfer targets with timing, price, and fixture context.</p>
        </div>
        <div className="placeholder-card">
          <h2>Sell List</h2>
          <p>Flag players with reduced appeal, poor fixtures, or expert concern.</p>
        </div>
        <div className="placeholder-card">
          <h2>Move Planner</h2>
          <p>Model one-week and multi-week transfer routes when squad data is available.</p>
        </div>
      </section>
    </PageShell>
  );
}
