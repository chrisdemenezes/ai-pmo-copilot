import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { aggregatePortfolio } from "@/lib/dashboard/aggregate";
import type { ProjectSummary } from "@/lib/dashboard/types";

/**
 * W1 -- FS-001 §5. Client-side reduce over the same payload as the grid
 * below. "Ações pendentes" links to the portfolio "Ações" page (TIP-008
 * Incremento 3) -- the other two KPIs stay plain stats, no page of their
 * own exists yet for them.
 */
export function PortfolioSummaryStrip({ projects }: { projects: ProjectSummary[] }) {
  const totals = aggregatePortfolio(projects);
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StripStat label="Projetos" value={totals.projectCount} />
      <StripStat label="Riscos identificados" value={totals.totalOpenRisks} />
      <StripStat label="Ações pendentes" value={totals.totalPendingActionItems} href="/actions" />
    </div>
  );
}

function StripStat({ label, value, href }: { label: string; value: number; href?: string }) {
  const content = (
    <CardContent className="p-5">
      <p className="text-xs text-ink-muted">{label}</p>
      <p className="font-mono text-2xl tabular-nums">{value}</p>
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
