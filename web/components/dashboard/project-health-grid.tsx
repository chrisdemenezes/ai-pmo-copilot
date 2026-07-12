import Link from "next/link";

import { cn } from "@/lib/utils";
import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ProjectSummary } from "@/lib/dashboard/types";

function workspaceHref(projectName: string) {
  return `/workspace/${encodeURIComponent(projectName)}`;
}

/**
 * W2 -- FS-001 §5/§11. Redesigned to a dense table for md/lg (Visual
 * Fidelity Sprint, Release 0.3) per RFC-001's own responsive decision --
 * "tabela vira lista de cards empilhados abaixo de 768px". Same 5 real
 * fields either way, no column added that doesn't already exist in
 * ProjectSummary.
 */
export function ProjectHealthGrid({ projects }: { projects: ProjectSummary[] }) {
  return (
    <>
      <div
        data-testid="project-table"
        className="hidden overflow-x-auto rounded-lg border border-border bg-surface shadow-md md:block"
      >
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
              <th className="px-4 py-3 font-medium">Projeto</th>
              <th className="px-4 py-3 font-medium">Saúde</th>
              <th className="px-4 py-3 font-medium">Análises</th>
              <th className="px-4 py-3 font-medium">Riscos identificados</th>
              <th className="px-4 py-3 font-medium">Ações pendentes</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr key={project.project_name} className="border-b border-border last:border-0">
                <td className="max-w-xs truncate px-4 py-3 font-display font-semibold">
                  <Link
                    href={workspaceHref(project.project_name)}
                    className="hover:text-accent hover:underline"
                    title={project.project_name}
                  >
                    {project.project_name}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <Badge variant={healthStatusVariant(project.latest_health_status)}>
                    {healthStatusLabel(project.latest_health_status)}
                  </Badge>
                </td>
                <td className="px-4 py-3 font-mono tabular-nums">{project.total_analyses}</td>
                <td
                  className={cn(
                    "px-4 py-3 font-mono tabular-nums",
                    project.open_risks > 0 && "text-warn",
                  )}
                  title="Total de riscos já identificados pela IA em análises deste projeto. Não indica se cada risco já foi tratado -- o produto ainda não rastreia esse ciclo de vida."
                >
                  {project.open_risks}
                </td>
                <td className="px-4 py-3 font-mono tabular-nums">{project.pending_action_items}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div data-testid="project-cards" className="flex flex-col gap-3 md:hidden">
        {projects.map((project) => (
          <Card key={project.project_name}>
            <CardContent className="flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <Link
                  href={workspaceHref(project.project_name)}
                  className="truncate font-display font-semibold hover:text-accent hover:underline"
                  title={project.project_name}
                >
                  {project.project_name}
                </Link>
                <Badge variant={healthStatusVariant(project.latest_health_status)}>
                  {healthStatusLabel(project.latest_health_status)}
                </Badge>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <Stat label="Análises" value={project.total_analyses} />
                <Stat
                  label="Riscos identificados"
                  value={project.open_risks}
                  emphasize={project.open_risks > 0}
                />
                <Stat label="Ações pendentes" value={project.pending_action_items} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}

function Stat({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: number;
  emphasize?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-ink-muted">{label}</p>
      <p className={cn("font-mono text-lg tabular-nums", emphasize && "text-warn")}>{value}</p>
    </div>
  );
}
