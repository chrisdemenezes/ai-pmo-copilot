"use client";

import { Badge, healthStatusLabel, healthStatusVariant } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Header } from "@/components/shell/header";
import { usePrograms } from "@/lib/hooks/use-programs";
import { useProjects } from "@/lib/hooks/use-projects";
import type { Program } from "@/lib/domain/program";
import type { Project } from "@/lib/domain/project";

/**
 * Project Delivery (Capability 03, Release 0.2) -- listagem funcional de
 * todos os Projects agrupados por Program pai. Sem CRUD (não solicitado
 * nesta Capability) -- apenas visualização real, mesma disciplina de
 * /program-management (Capability 02).
 */
export default function ProjectDeliveryPage() {
  const programs = usePrograms();
  const projects = useProjects();

  if (programs.isPending || projects.isPending) {
    return <ProjectDeliverySkeleton />;
  }

  if (programs.isError && !programs.data) throw programs.error;
  if (projects.isError && !projects.data) throw projects.error;

  const programList = programs.data ?? [];
  const projectList = projects.data ?? [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            STRATECH · Project Delivery
          </p>
          <h1 className="font-display text-2xl font-semibold">Projects por Program</h1>
        </div>
      </Header>

      {programList.map((program) => {
        const ownProjects = projectList.filter((project) => project.belongsToProgram(program.id));
        return <ProgramProjectsSection key={program.id} program={program} projects={ownProjects} />;
      })}
    </main>
  );
}

function ProgramProjectsSection({ program, projects }: { program: Program; projects: Project[] }) {
  return (
    <section className="flex flex-col gap-3">
      <Card>
        <CardHeader>
          <CardTitle>{program.name}</CardTitle>
          <CardDescription>
            {projects.length} {projects.length === 1 ? "Project" : "Projects"} — {program.programManager}
          </CardDescription>
        </CardHeader>
      </Card>

      {projects.length === 0 ? (
        <Card>
          <CardContent className="p-5 text-sm text-ink-muted">
            Nenhum Project vinculado a este Program ainda.
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Projeto</TableHead>
                <TableHead>Saúde</TableHead>
                <TableHead>Progresso</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Sponsor</TableHead>
                <TableHead>Project Manager</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map((project) => (
                <TableRow key={project.id}>
                  <TableCell className="font-display font-semibold">{project.name}</TableCell>
                  <TableCell>
                    <Badge variant={healthStatusVariant(project.health())}>
                      {healthStatusLabel(project.health())}
                    </Badge>
                  </TableCell>
                  <TableCell className="w-40">
                    <div className="flex items-center gap-2">
                      <Progress value={project.completionPercentage()} className="w-24" />
                      <span className="font-mono text-xs tabular-nums text-ink-muted">
                        {project.completionPercentage()}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-ink-muted">{project.status}</TableCell>
                  <TableCell className="text-ink-muted">{project.sponsor}</TableCell>
                  <TableCell className="text-ink-muted">{project.projectManager}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}

function ProjectDeliverySkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-48" />
      <Skeleton className="h-48" />
    </main>
  );
}
