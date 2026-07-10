import { Card, CardContent } from "@/components/ui/card";
import { aggregatePortfolio } from "@/lib/dashboard/aggregate";
import type { ProjectSummary } from "@/lib/dashboard/types";

/** W1 -- FS-001 §5. Client-side reduce over the same payload as the grid below. */
export function PortfolioSummaryStrip({ projects }: { projects: ProjectSummary[] }) {
  const totals = aggregatePortfolio(projects);
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StripStat label="Projetos" value={totals.projectCount} />
      <StripStat label="Riscos identificados" value={totals.totalOpenRisks} />
      <StripStat label="Ações pendentes" value={totals.totalPendingActionItems} />
    </div>
  );
}

function StripStat({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-xs text-ink-muted">{label}</p>
        <p className="font-mono text-2xl tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}
