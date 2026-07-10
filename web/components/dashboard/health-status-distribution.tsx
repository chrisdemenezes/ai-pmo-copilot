import { Badge, healthStatusVariant } from "@/components/ui/badge";
import { groupByHealthStatus, type HealthStatusKey } from "@/lib/dashboard/aggregate";
import type { ProjectSummary } from "@/lib/dashboard/types";

const LABELS: Record<HealthStatusKey, string> = {
  green: "Saudável",
  yellow: "Atenção",
  red: "Crítico",
  none: "Sem dado",
};

/** W3 -- FS-001 §5. Same payload as W1/W2, no extra request. */
export function HealthStatusDistribution({ projects }: { projects: ProjectSummary[] }) {
  const counts = groupByHealthStatus(projects);
  const keys = Object.keys(counts) as HealthStatusKey[];

  return (
    <div className="flex flex-wrap gap-4">
      {keys.map((key) => (
        <div key={key} className="flex items-center gap-2">
          <Badge variant={key === "none" ? "neutral" : healthStatusVariant(key)}>
            {LABELS[key]}
          </Badge>
          <span className="font-mono text-sm tabular-nums">{counts[key]}</span>
        </div>
      ))}
    </div>
  );
}
