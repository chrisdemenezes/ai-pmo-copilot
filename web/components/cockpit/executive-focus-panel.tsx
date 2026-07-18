import Link from "next/link";
import { Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ExecutiveFocusItem } from "@/lib/dashboard/executive-focus";

/**
 * Entrega 2.4 -- "Onde devo concentrar minha atenção hoje?" Primeiro
 * elemento visual do Executive Cockpit (Product Review Sprint 1.4).
 * Calculado a partir de dado real -- ver lib/dashboard/executive-focus.ts.
 */
export function ExecutiveFocusPanel({ focus }: { focus: ExecutiveFocusItem | null }) {
  if (!focus) {
    return (
      <Card className="border-ok bg-ok-soft">
        <CardContent className="flex items-center gap-3 p-5">
          <Target className="size-5 text-ok" aria-hidden="true" />
          <p className="text-sm text-ink">
            Nenhum ponto de atenção crítico identificado no portfólio agora.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Link href={focus.href} className="block">
      <Card className="border-accent bg-accent-soft transition-colors hover:bg-accent-soft/80">
        <CardContent className="flex items-start gap-4 p-5">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent text-white">
            <Target className="size-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Badge variant="danger">{focus.subtitle}</Badge>
            </div>
            <p className="mt-1 font-display text-xl font-semibold text-ink">{focus.title}</p>
            <p className="mt-1 text-sm text-ink-muted">{focus.reason}</p>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
