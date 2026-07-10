import { Badge, healthStatusVariant } from "@/components/ui/badge";
import { rankByRisk } from "@/lib/dashboard/aggregate";
import type { ProjectSummary } from "@/lib/dashboard/types";

/** W5 -- FS-001 §5. Same payload as W1/W2, client-side sort/slice only. */
export function RiskConcentrationRanking({ projects }: { projects: ProjectSummary[] }) {
  const ranked = rankByRisk(projects);

  if (ranked.length === 0) {
    return <p className="text-sm text-ink-muted">Nenhum projeto com riscos identificados.</p>;
  }

  return (
    <ol className="flex flex-col gap-2">
      {ranked.map((project) => (
        <li
          key={project.project_name}
          className="flex items-center justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2"
        >
          <span className="truncate" title={project.project_name}>
            {project.project_name}
          </span>
          <span className="flex items-center gap-2">
            <Badge variant={healthStatusVariant(project.latest_health_status)}>
              {project.latest_health_status ?? "sem dado"}
            </Badge>
            <span className="font-mono text-sm tabular-nums">{project.open_risks}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
