import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { PendingDecision } from "@/lib/mock/cockpit-data";

/** Entrega 2.4 -- Decision Center (dados simulados). */
export function DecisionCenterPanel({ decisions }: { decisions: PendingDecision[] }) {
  return (
    <Card>
      <CardContent className="flex flex-col divide-y divide-border p-0">
        {decisions.map((decision) => (
          <div
            key={decision.title + decision.context}
            className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="font-display font-semibold text-ink">{decision.title}</p>
              <p className="text-sm text-ink-muted">{decision.context}</p>
              <p className="mt-1 text-xs text-ink-faint">
                Solicitado por {decision.requestedBy} · há {decision.daysPending}{" "}
                {decision.daysPending === 1 ? "dia" : "dias"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {decision.daysPending >= 3 ? <Badge variant="warn">Aguardando há dias</Badge> : null}
              <Link href="/decisions">
                <Button variant="outline" size="sm">
                  Revisar
                </Button>
              </Link>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
