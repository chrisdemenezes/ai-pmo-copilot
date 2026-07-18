import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import type { CockpitKPI } from "@/lib/mock/cockpit-data";

/**
 * Entrega 2.1 -- Executive Cockpit, dados simulados (Sprint 1). Mesmo
 * padrão visual do PortfolioSummaryStrip (V1), generalizado para os
 * indicadores de nível STRATECH V2 (Portfólio/Programa/Projeto).
 */
export function CockpitKpiStrip({ kpis }: { kpis: CockpitKPI[] }) {
  return (
    <div
      data-testid="cockpit-kpi-strip"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      {kpis.map((kpi) => {
        const content = (
          <CardContent className="p-5">
            <p className="text-xs text-ink-muted">{kpi.label}</p>
            <p className="font-mono text-2xl tabular-nums">{kpi.value}</p>
          </CardContent>
        );
        if (kpi.href) {
          return (
            <Link key={kpi.label} href={kpi.href} className="block">
              <Card className="transition-colors hover:bg-surface-2">{content}</Card>
            </Link>
          );
        }
        return <Card key={kpi.label}>{content}</Card>;
      })}
    </div>
  );
}
