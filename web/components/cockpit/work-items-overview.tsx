import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { WorkItemBreakdown } from "@/lib/mock/cockpit-data";

/**
 * Entrega 2.3 -- Demandas/Riscos/Issues/Mudanças (Sprint 1, dados
 * simulados). Nenhuma das 4 categorias é uma entidade real hoje --
 * candidatas a ADR de extensão do Domain Map (ver Architecture Evolution
 * Proposal, Seção 8).
 */
export function WorkItemsOverview({ items }: { items: WorkItemBreakdown[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item.category}>
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <CardTitle>{item.category}</CardTitle>
              {item.critical > 0 ? (
                <Badge variant="danger">{item.critical} crítico(s)</Badge>
              ) : null}
            </div>
            <CardDescription>{item.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-mono text-3xl tabular-nums">{item.total}</p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-ink-muted">
              <div>
                <p>Aberto</p>
                <p className="font-mono text-sm tabular-nums text-ink">{item.open}</p>
              </div>
              <div>
                <p>Em andamento</p>
                <p className="font-mono text-sm tabular-nums text-ink">{item.inProgress}</p>
              </div>
              <div>
                <p>Concluído</p>
                <p className="font-mono text-sm tabular-nums text-ink">{item.resolved}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
