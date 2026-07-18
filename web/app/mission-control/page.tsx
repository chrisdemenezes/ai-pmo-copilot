import { Check } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Header } from "@/components/shell/header";
import {
  EPIC_STATUS,
  RELEASE_STATUS,
  PULL_REQUESTS,
  GOVERNANCE_SUMMARY,
  SPRINT_1_ENTREGAS,
  RECENT_DECISIONS,
  PRODUCT_PULSE_TODAY,
  PRODUCT_DNA_STATEMENT,
  type EpicStatus,
} from "@/lib/mock/mission-control-data";

/**
 * Mission Control -- painel exclusivo do Founder para acompanhar a
 * evolução do produto (Sprint 1, Diretriz Complementar).
 *
 * LIMITAÇÃO CONHECIDA: esta rota não é tecnicamente restrita ao Founder
 * ainda -- RBAC funcional é o Épico 3 (Not Started). Até lá, qualquer
 * usuário autenticado pode acessá-la. Reportado explicitamente, não
 * ocultado.
 */
export default function MissionControlPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <Header>
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
            STRATECH · Mission Control
          </p>
          <h1 className="font-display text-2xl font-semibold">Painel do Founder</h1>
        </div>
        <Badge variant="outline">Acesso não restrito ainda — RBAC no Épico 3</Badge>
      </Header>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">Product Pulse</h2>
        <Card>
          <CardContent className="flex flex-col gap-4 p-5">
            <div>
              <div className="flex items-baseline justify-between">
                <p className="font-display font-semibold text-ink">Release 0.1</p>
                <span className="font-mono text-sm tabular-nums text-ink-muted">
                  {RELEASE_STATUS[0].progress}% concluída
                </span>
              </div>
              <Progress value={RELEASE_STATUS[0].progress} className="mt-2" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                Hoje a STRATECH evoluiu
              </p>
              <ul className="mt-2 flex flex-col gap-1.5">
                {PRODUCT_PULSE_TODAY.map((entry) => (
                  <li key={entry.label} className="flex items-start gap-2 text-sm text-ink">
                    <Check className="mt-0.5 size-4 shrink-0 text-ok" aria-hidden="true" />
                    {entry.label}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">Product DNA</h2>
        <Card className="border-accent bg-accent-soft">
          <CardContent className="p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-accent-ink">
              Nossa missão
            </p>
            <p className="mt-1 font-display text-lg text-ink">{PRODUCT_DNA_STATEMENT}</p>
          </CardContent>
        </Card>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">Sprint 1 — Entregas</h2>
        <div className="flex flex-wrap gap-2">
          {SPRINT_1_ENTREGAS.map((entrega) => (
            <Badge
              key={entrega.id}
              variant={
                entrega.status === "Concluído"
                  ? "ok"
                  : entrega.status === "Em andamento"
                    ? "warn"
                    : "neutral"
              }
            >
              {entrega.id}: {entrega.label}
            </Badge>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">Épicos — Release 0.1</h2>
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Épico</TableHead>
                <TableHead>Nome</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Detalhe</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {EPIC_STATUS.map((epic) => (
                <TableRow key={epic.code}>
                  <TableCell className="font-display font-semibold">{epic.code}</TableCell>
                  <TableCell>{epic.name}</TableCell>
                  <TableCell>
                    <Badge variant={epicStatusVariant(epic.status)}>{epic.status}</Badge>
                  </TableCell>
                  <TableCell className="text-ink-muted">{epic.detail}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">Releases (0.1 → 0.5)</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {RELEASE_STATUS.map((release) => (
            <Card key={release.version}>
              <CardHeader>
                <CardTitle>Release {release.version}</CardTitle>
                <CardDescription>{release.name}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Progress value={release.progress} />
                  <span className="font-mono text-xs tabular-nums text-ink-muted">
                    {release.progress}%
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">Pull Requests recentes</h2>
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>PR</TableHead>
                <TableHead>Título</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {PULL_REQUESTS.map((pr) => (
                <TableRow key={pr.number}>
                  <TableCell className="font-mono">#{pr.number}</TableCell>
                  <TableCell>{pr.title}</TableCell>
                  <TableCell>
                    <Badge variant={pr.status === "Merged" ? "ok" : "warn"}>{pr.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">Governança</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-ink-muted">Débito técnico aberto</p>
              <p className="font-mono text-2xl tabular-nums">{GOVERNANCE_SUMMARY.technicalDebtOpen}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-ink-muted">Baseline Defects</p>
              <p className="font-mono text-2xl tabular-nums">{GOVERNANCE_SUMMARY.baselineDefects}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-ink-muted">ADRs registradas</p>
              <p className="font-mono text-2xl tabular-nums">{GOVERNANCE_SUMMARY.adrCount}</p>
              {GOVERNANCE_SUMMARY.adrCollision ? (
                <Badge variant="danger" className="mt-1">
                  1 colisão pendente
                </Badge>
              ) : null}
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-ink-muted">Lessons Learned</p>
              <p className="font-mono text-2xl tabular-nums">{GOVERNANCE_SUMMARY.lessonsLearned}</p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">Decision Log — recentes</h2>
        <Card>
          <CardContent className="flex flex-col gap-3 p-5">
            {RECENT_DECISIONS.map((decision) => (
              <div key={decision.id} className="flex items-start gap-3 text-sm">
                <Badge variant="outline">{decision.id}</Badge>
                <p className="text-ink">{decision.summary}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}

function epicStatusVariant(status: EpicStatus) {
  if (status === "Merged") return "ok" as const;
  if (status === "In Progress") return "warn" as const;
  return "neutral" as const;
}
