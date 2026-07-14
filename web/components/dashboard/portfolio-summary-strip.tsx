import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { aggregatePortfolio } from "@/lib/dashboard/aggregate";
import type { ProjectSummary } from "@/lib/dashboard/types";

/**
 * W1 -- FS-001 §5. Client-side reduce over the same payload as the grid
 * below. "Ações pendentes" links to the portfolio "Ações" page (TIP-008
 * Incremento 3). "Decisões críticas" links to the Executive Decision
 * Queue (TIP-009 Incremento 3) -- criticalDecisionsCount is computed once,
 * by the Dashboard page, via the same buildExecutiveDecisionQueue() the
 * /decisions page uses (Single Decision Source, TIP-009 §08) -- this
 * component never recalculates it. null while the Risco signal hasn't
 * resolved yet -- shows a placeholder instead of a possibly-wrong count
 * (Executive Trust).
 */
export function PortfolioSummaryStrip({
  projects,
  criticalDecisionsCount,
}: {
  projects: ProjectSummary[];
  criticalDecisionsCount: number | null;
}) {
  const totals = aggregatePortfolio(projects);
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
      <StripStat label="Projetos" value={totals.projectCount} />
      <StripStat label="Riscos identificados" value={totals.totalOpenRisks} />
      <StripStat label="Ações pendentes" value={totals.totalPendingActionItems} href="/actions" />
      <StripStat label="Decisões críticas" value={criticalDecisionsCount} href="/decisions" />
    </div>
  );
}

function StripStat({
  label,
  value,
  href,
}: {
  label: string;
  value: number | null;
  href?: string;
}) {
  const content = (
    <CardContent className="p-5">
      <p className="text-xs text-ink-muted">{label}</p>
      {value === null ? (
        <Skeleton className="mt-1 h-7 w-10" />
      ) : (
        <p className="font-mono text-2xl tabular-nums">{value}</p>
      )}
    </CardContent>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        <Card className="transition-colors hover:bg-surface-2">{content}</Card>
      </Link>
    );
  }

  return <Card>{content}</Card>;
}
