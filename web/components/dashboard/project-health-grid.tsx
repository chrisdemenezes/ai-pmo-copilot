import { cn } from "@/lib/utils";
import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProjectSummary } from "@/lib/dashboard/types";

/**
 * W2 -- FS-001 §5/§11. auto-fill/minmax (not fixed columns) so the grid
 * reads well with 1 project or 50 -- UX Review §2 layout note.
 */
export function ProjectHealthGrid({ projects }: { projects: ProjectSummary[] }) {
  return (
    <div
      className="grid gap-4"
      style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}
    >
      {projects.map((project) => (
        <Card key={project.project_name}>
          <CardHeader className="flex-row items-start justify-between gap-2">
            <CardTitle className="truncate" title={project.project_name}>
              {project.project_name}
            </CardTitle>
            <Badge variant={healthStatusVariant(project.latest_health_status)}>
              {healthStatusLabel(project.latest_health_status)}
            </Badge>
          </CardHeader>
          <CardContent className="grid grid-cols-3 gap-3">
            <Stat label="Análises" value={project.total_analyses} />
            <Stat
              label="Riscos identificados"
              value={project.open_risks}
              title="Total de riscos já identificados pela IA em análises deste projeto. Não indica se cada risco já foi tratado -- o produto ainda não rastreia esse ciclo de vida."
              emphasize={project.open_risks > 0}
            />
            <Stat label="Ações pendentes" value={project.pending_action_items} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function Stat({
  label,
  value,
  title,
  emphasize,
}: {
  label: string;
  value: number;
  title?: string;
  emphasize?: boolean;
}) {
  return (
    <div title={title}>
      <p className="text-xs text-ink-muted">{label}</p>
      <p className={cn("font-mono text-lg tabular-nums", emphasize && "text-warn")}>{value}</p>
    </div>
  );
}
