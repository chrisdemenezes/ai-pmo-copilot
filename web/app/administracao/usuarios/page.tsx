"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
import { useAdminUsers } from "@/lib/hooks/use-admin-users";
import { useAdminRoles } from "@/lib/hooks/use-admin-roles";
import { useAdminUserRolesIndex } from "@/lib/hooks/use-admin-user-roles-index";
import { CreateUserDialog } from "./create-user-dialog";
import { EditUserDialog } from "./edit-user-dialog";
import { ToggleStatusButton } from "./toggle-status-button";
import { UserRolesDialog } from "./user-roles-dialog";

const STATUS_ALL = "all";
const STATUS_ACTIVE = "active";
const STATUS_INACTIVE = "inactive";
const ROLE_ALL = "all";

/**
 * User Management (Enterprise Administration, Wave 2) -- listar,
 * pesquisar, filtrar por status/papel, cadastrar, editar, ativar/
 * inativar e associar/remover papéis. Primeira tela administrativa da
 * STRATECH (Backend -> BFF -> Frontend completo).
 */
export default function UsersAdminPage() {
  const users = useAdminUsers();
  const roles = useAdminRoles();
  const rolesIndex = useAdminUserRolesIndex();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState(STATUS_ALL);
  const [roleFilter, setRoleFilter] = useState(ROLE_ALL);

  const filteredUsers = useMemo(() => {
    const list = users.data ?? [];
    const index = rolesIndex.data ?? {};
    const term = search.trim().toLowerCase();

    return list.filter((user) => {
      if (term.length > 0) {
        const matchesTerm =
          user.displayName.toLowerCase().includes(term) ||
          user.email.toLowerCase().includes(term);
        if (!matchesTerm) return false;
      }
      if (statusFilter === STATUS_ACTIVE && !user.isActive) return false;
      if (statusFilter === STATUS_INACTIVE && user.isActive) return false;
      if (roleFilter !== ROLE_ALL) {
        const userRoles = index[user.id] ?? [];
        if (!userRoles.includes(roleFilter)) return false;
      }
      return true;
    });
  }, [users.data, rolesIndex.data, search, statusFilter, roleFilter]);

  if (users.isPending) {
    return <UsersAdminSkeleton />;
  }

  if (users.isError) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
        <Header>
          <PageTitle />
        </Header>
        <Card>
          <CardContent className="p-5 text-sm text-danger" role="alert">
            Falha ao carregar usuários.
          </CardContent>
        </Card>
      </main>
    );
  }

  const roleNamesIndex = rolesIndex.data ?? {};

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <PageTitle />
        <CreateUserDialog />
      </Header>

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Pesquisar por nome ou e-mail"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="max-w-xs"
          aria-label="Pesquisar usuários"
        />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger aria-label="Filtrar por status">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={STATUS_ALL}>Todos os status</SelectItem>
            <SelectItem value={STATUS_ACTIVE}>Ativos</SelectItem>
            <SelectItem value={STATUS_INACTIVE}>Inativos</SelectItem>
          </SelectContent>
        </Select>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger aria-label="Filtrar por papel">
            <SelectValue placeholder="Papel" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ROLE_ALL}>Todos os papéis</SelectItem>
            {(roles.data ?? []).map((role) => (
              <SelectItem key={role.id} value={role.name}>
                {role.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {filteredUsers.length === 0 ? (
        <Card>
          <CardContent className="p-5 text-sm text-ink-muted">
            {(users.data ?? []).length === 0
              ? "Nenhum usuário cadastrado ainda."
              : "Nenhum usuário corresponde à busca/filtros atuais."}
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>E-mail</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Papéis</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.displayName}</TableCell>
                  <TableCell className="text-ink-muted">{user.email}</TableCell>
                  <TableCell>
                    <Badge variant={user.isActive ? "ok" : "neutral"}>
                      {user.isActive ? "Ativo" : "Inativo"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {(roleNamesIndex[user.id] ?? []).map((roleName) => (
                        <Badge key={roleName} variant="outline">
                          {roleName}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <EditUserDialog user={user} />
                      <UserRolesDialog user={user} />
                      <ToggleStatusButton user={user} />
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
      <h1 className="font-display text-2xl font-semibold">Usuários</h1>
    </div>
  );
}

function UsersAdminSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      <Header>
        <PageTitle />
      </Header>
      <Skeleton className="h-9 w-full max-w-xs" />
      <div className="flex flex-col gap-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </main>
  );
}
