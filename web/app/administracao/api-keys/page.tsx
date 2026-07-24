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
import { useAdminApiKeys } from "@/lib/hooks/use-admin-api-keys";
import { CreateApiKeyDialog } from "./create-api-key-dialog";
import { RevokeApiKeyButton } from "./revoke-api-key-button";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/**
 * API Keys (D-051, Enterprise Administration) -- credencial fundamental
 * para acesso programático à API, ao lado de Usuários/Papéis/Auditoria.
 * Não é um artefato do Integration Hub: qualquer consumidor futuro
 * (Integration Hub incluso) se autentica através dela, nunca o contrário.
 */
export default function ApiKeysAdminPage() {
  const apiKeys = useAdminApiKeys();

  if (apiKeys.isPending) {
    return <ApiKeysAdminSkeleton />;
  }

  if (apiKeys.isError) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
        <Header>
          <PageTitle />
        </Header>
        <Card>
          <CardContent className="p-5 text-sm text-danger" role="alert">
            Falha ao carregar chaves de API.
          </CardContent>
        </Card>
      </main>
    );
  }

  const keys = apiKeys.data ?? [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <PageTitle />
        <CreateApiKeyDialog />
      </Header>

      {keys.length === 0 ? (
        <Card>
          <CardContent className="p-5 text-sm text-ink-muted">
            Nenhuma chave de API criada ainda.
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Prefixo</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Criada em</TableHead>
                <TableHead>Último uso</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((apiKey) => (
                <TableRow key={apiKey.id}>
                  <TableCell className="font-medium">{apiKey.name}</TableCell>
                  <TableCell className="font-mono text-xs text-ink-muted">
                    {apiKey.keyPrefix}…
                  </TableCell>
                  <TableCell>
                    <Badge variant={apiKey.revokedAt ? "neutral" : "ok"}>
                      {apiKey.revokedAt ? "Revogada" : "Ativa"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-ink-muted">{formatDate(apiKey.createdAt)}</TableCell>
                  <TableCell className="text-ink-muted">
                    {apiKey.lastUsedAt ? formatDate(apiKey.lastUsedAt) : "Nunca usada"}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      {!apiKey.revokedAt && <RevokeApiKeyButton apiKey={apiKey} />}
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
      <h1 className="font-display text-2xl font-semibold">Chaves de API</h1>
    </div>
  );
}

function ApiKeysAdminSkeleton() {
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
