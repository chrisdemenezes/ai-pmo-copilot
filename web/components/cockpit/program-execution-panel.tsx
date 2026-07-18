import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { Program } from "@/lib/domain/program";
import { countCriticalProjects, rankProjectsNeedingAttention, type Project } from "@/lib/domain/project";

/**
 * Program Execution (Capability 03) -- por Program: quantidade de
 * Projects, progresso, saúde, Projetos Críticos; abaixo, Top 5 Projects
 * que exigem atenção (ranqueado por risco via rankProjectsNeedingAttention).
 * `programs` já deve vir consolidado (consolidatePrograms()) para que os
 * números aqui e no grid de Programas concordem.
 */
export function ProgramExecutionPanel({
  programs,
  projects,
}: {
  programs: Program[];
  projects: Project[];
}) {
  const topAttention = rankProjectsNeedingAttention(projects, 5);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {programs.map((program) => {
          const criticalCount = countCriticalProjects(program.id, projects);
          return (
            <Card key={program.id}>
              <CardHeader>
                <CardTitle>{program.name}</CardTitle>
                <CardDescription>
                  {program.projectCount} {program.projectCount === 1 ? "Project" : "Projects"}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <Progress value={program.progressPercentage} />
                  <span className="font-mono text-xs tabular-nums text-ink-muted">
                    {program.progressPercentage}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <Badge variant={healthStatusVariant(program.health)}>
                    {healthStatusLabel(program.health)}
                  </Badge>
                  {criticalCount > 0 ? (
                    <Badge variant="danger">
                      {criticalCount} {criticalCount === 1 ? "crítico" : "críticos"}
                    </Badge>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Top 5 Projects que exigem atenção</CardTitle>
          <CardDescription>Ordenado por risco (saúde, depois menor progresso).</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {topAttention.length === 0 ? (
            <p className="text-sm text-ink-muted">Nenhum Project cadastrado ainda.</p>
          ) : (
            topAttention.map((project) => (
              <div
                key={project.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2 text-sm"
              >
                <span className="font-display font-semibold">{project.name}</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs tabular-nums text-ink-muted">
                    {project.completionPercentage()}%
                  </span>
                  <Badge variant={healthStatusVariant(project.health())}>
                    {healthStatusLabel(project.health())}
                  </Badge>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
