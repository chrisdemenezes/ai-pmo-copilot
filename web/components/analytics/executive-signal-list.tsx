import { AlertTriangle, Info, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExecutiveSignal, SignalSeverity } from "@/lib/domain/executive-signal";

const SEVERITY_BADGE: Record<SignalSeverity, "danger" | "warn" | "neutral"> = {
  critical: "danger",
  warning: "warn",
  info: "neutral",
};

const SEVERITY_LABEL: Record<SignalSeverity, string> = {
  critical: "Crítico",
  warning: "Atenção",
  info: "Informativo",
};

function SignalIcon({ signal }: { signal: ExecutiveSignal }) {
  if (signal.type === "recovery_trend") return <TrendingUp className="size-4 text-ok" aria-hidden="true" />;
  if (signal.severity === "critical") return <AlertTriangle className="size-4 text-danger" aria-hidden="true" />;
  return <Info className="size-4 text-ink-faint" aria-hidden="true" />;
}

/**
 * Wave 8 (Executive Analytics), Section 8 -- renders deterministic
 * Executive Signals as informational cards. A Signal is never a
 * Decision/Recommendation and never triggers an action from here -- it is
 * strictly "a fact that deserves attention," shown with its evidence
 * reference so the reader can verify it against real data.
 */
export function ExecutiveSignalList({ signals }: { signals: ExecutiveSignal[] }) {
  if (signals.length === 0) {
    return (
      <Card data-testid="executive-signal-list">
        <CardContent className="p-5">
          <p className="text-sm text-ink-faint">Nenhum sinal executivo no momento.</p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card data-testid="executive-signal-list">
      <CardHeader>
        <CardTitle>Sinais Executivos</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 p-5 pt-0">
        {signals.map((signal) => (
          <div key={`${signal.type}-${signal.scope}-${signal.asOf}`} className="flex items-start gap-2">
            <SignalIcon signal={signal} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-ink">{signal.metric}</p>
                <Badge variant={SEVERITY_BADGE[signal.severity]}>{SEVERITY_LABEL[signal.severity]}</Badge>
              </div>
              <p className="text-xs text-ink-muted">{signal.evidenceReference}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
