"use client";

import { Badge } from "@/components/ui/badge";
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
import type { InvitationStatus } from "@/lib/domain/invitation";
import { useAdminInvitations } from "@/lib/hooks/use-admin-invitations";
import { CreateInvitationDialog } from "./create-invitation-dialog";
import { CancelInvitationButton } from "./cancel-invitation-button";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

const STATUS_LABEL: Record<InvitationStatus, string> = {
  pending: "Pendente",
  accepted: "Aceito",
  expired: "Expirado",
  cancelled: "Cancelado",
};

const STATUS_VARIANT: Record<InvitationStatus, "ok" | "neutral" | "warn"> = {
  pending: "warn",
  accepted: "ok",
  expired: "neutral",
  cancelled: "neutral",
};

/**
 * Convites (D-054, Enterprise Administration) -- credencial de onboarding
 * fundamental, ao lado de Usuários/Papéis/API Keys/Sessões. O e-mail é
 * apenas o mecanismo de entrega (abstraído em NotificationProvider, NoOp
 * hoje): o link do convite é entregue manualmente até um provedor existir.
 */
export default function InvitationsAdminPage() {
  const invitations = useAdminInvitations();

  if (invitations.isPending) {
    return <InvitationsAdminSkeleton />;
  }

  if (invitations.isError) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
        <Header>
          <PageTitle />
        </Header>
        <Card>
          <CardContent className="p-5 text-sm text-danger" role="alert">
            Falha ao carregar convites.
          </CardContent>
        </Card>
      </main>
    );
  }

  const rows = invitations.data ?? [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <PageTitle />
        <CreateInvitationDialog />
      </Header>

      {rows.length === 0 ? (
        <Card>
          <CardContent className="p-5 text-sm text-ink-muted">
            Nenhum convite emitido ainda.
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>E-mail</TableHead>
                <TableHead>Papel</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Criado em</TableHead>
                <TableHead>Expira em</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((invitation) => (
                <TableRow key={invitation.id}>
                  <TableCell className="font-medium">{invitation.email}</TableCell>
                  <TableCell className="text-ink-muted">{invitation.roleName}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[invitation.status]}>
                      {STATUS_LABEL[invitation.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-ink-muted">
                    {formatDate(invitation.createdAt)}
                  </TableCell>
                  <TableCell className="text-ink-muted">
                    {formatDate(invitation.expiresAt)}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      {invitation.status === "pending" && (
                        <CancelInvitationButton invitation={invitation} />
                      )}
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
      <h1 className="font-display text-2xl font-semibold">Convites</h1>
    </div>
  );
}

function InvitationsAdminSkeleton() {
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
