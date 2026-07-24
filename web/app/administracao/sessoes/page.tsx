"use client";

import { Card, CardContent } from "@/components/ui/card";
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
import { useAdminSessions } from "@/lib/hooks/use-admin-sessions";
import { RevokeSessionButton } from "./revoke-session-button";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Sessões (item 5 do Wave Completion Review retrospectivo, resolve TD-010) --
 * lista as sessões de login ativas da organização e permite revogá-las antes
 * da expiração natural de 12h. O registro server-side (tabela `sessions`) é o
 * que torna a revogação possível -- antes, "logout" era só o cliente
 * descartando o cookie.
 */
export default function SessionsAdminPage() {
  const sessions = useAdminSessions();

  if (sessions.isPending) {
    return <SessionsAdminSkeleton />;
  }

  if (sessions.isError) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
        <Header>
          <PageTitle />
        </Header>
        <Card>
          <CardContent className="p-5 text-sm text-danger" role="alert">
            Falha ao carregar sessões.
          </CardContent>
        </Card>
      </main>
    );
  }

  const rows = sessions.data ?? [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <PageTitle />
      </Header>

      {rows.length === 0 ? (
        <Card>
          <CardContent className="p-5 text-sm text-ink-muted">
            Nenhuma sessão ativa no momento.
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Usuário</TableHead>
                <TableHead>Sessão</TableHead>
                <TableHead>Iniciada em</TableHead>
                <TableHead>Último acesso</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((session) => (
                <TableRow key={session.id}>
                  <TableCell className="font-medium">Usuário #{session.userId}</TableCell>
                  <TableCell className="font-mono text-xs text-ink-muted">
                    {session.id.slice(0, 8)}…
                  </TableCell>
                  <TableCell className="text-ink-muted">
                    {formatDateTime(session.createdAt)}
                  </TableCell>
                  <TableCell className="text-ink-muted">
                    {session.lastSeenAt ? formatDateTime(session.lastSeenAt) : "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <RevokeSessionButton session={session} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </main>
  );
}

function PageTitle() {
  return (
    <div>
      <p className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
        STRATECH · Administração
      </p>
      <h1 className="font-display text-2xl font-semibold">Sessões</h1>
    </div>
  );
}

function SessionsAdminSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <PageTitle />
      </Header>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </main>
  );
}
