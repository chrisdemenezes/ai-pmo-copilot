import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { groupByHealthStatus, type HealthStatusKey } from "@/lib/dashboard/aggregate";
import type { ProjectSummary } from "@/lib/dashboard/types";

const KEY_TO_STATUS: Record<HealthStatusKey, "green" | "yellow" | "red" | null> = {
  green: "green",
  yellow: "yellow",
  red: "red",
  none: null,
};

/** W3 -- FS-001 §5. Same payload as W1/W2, no extra request. */
export function HealthStatusDistribution({ projects }: { projects: ProjectSummary[] }) {
  const counts = groupByHealthStatus(projects);
  const keys = Object.keys(counts) as HealthStatusKey[];

  return (
    <div className="flex flex-wrap gap-4">
      {keys.map((key) => (
        <div key={key} className="flex items-center gap-2">
          <Badge variant={healthStatusVariant(KEY_TO_STATUS[key])}>
            {healthStatusLabel(KEY_TO_STATUS[key])}
          </Badge>
          <span className="font-mono text-sm tabular-nums">{counts[key]}</span>
        </div>
      ))}
    </div>
  );
}
