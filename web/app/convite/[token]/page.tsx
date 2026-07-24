"use client";

import { use, useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AdminApiError,
  acceptInvitation,
  previewInvitation,
  type InvitationPreview,
} from "@/lib/domain/invitation";

/**
 * Convites (D-054) -- public acceptance page. Outside the session gate
 * (proxy.ts): the invitee has no account yet; the token in the URL is the
 * authorization. They set their own name + password; email, organization
 * and role come from the invitation, never editable here.
 */
export default function AcceptInvitationPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const router = useRouter();

  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    previewInvitation(token)
      .then((data) => {
        if (!cancelled) setPreview(data);
      })
      .catch(() => {
        if (!cancelled) setLoadError("Convite inválido ou não encontrado.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (displayName.trim().length === 0 || password.length === 0 || pending) return;
    setPending(true);
    setSubmitError(null);
    try {
      await acceptInvitation(token, displayName.trim(), password);
      router.push("/entrar");
    } catch (reason) {
      setPending(false);
      setSubmitError(
        reason instanceof AdminApiError ? reason.message : "Não foi possível aceitar o convite.",
      );
    }
  }

  return (
    <main className="flex min-h-full flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Aceitar convite</CardTitle>
          <CardDescription>Crie sua conta na STRATECH.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-ink-muted">Carregando convite…</p>
          ) : loadError ? (
            <p role="alert" className="text-sm text-danger">
              {loadError}
            </p>
          ) : preview && preview.status !== "pending" ? (
            <p role="alert" className="text-sm text-danger">
              Este convite não está mais disponível ({statusLabel(preview.status)}).
            </p>
          ) : preview ? (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <p className="text-sm text-ink-muted" data-testid="invitation-summary">
                Você foi convidado para <strong>{preview.organizationName}</strong> como{" "}
                <strong>{preview.roleName}</strong>, usando o e-mail{" "}
                <strong>{preview.email}</strong>.
              </p>

              <div className="flex flex-col gap-2">
                <Label htmlFor="accept-name">Seu nome</Label>
                <Input
                  id="accept-name"
                  required
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="accept-password">Senha</Label>
                <Input
                  id="accept-password"
                  type="password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>

              {submitError && (
                <p role="alert" className="text-sm text-danger">
                  {submitError}
                </p>
              )}

              <Button
                type="submit"
                disabled={displayName.trim().length === 0 || password.length === 0 || pending}
              >
                {pending ? "Aceitando…" : "Aceitar e criar conta"}
              </Button>
            </form>
          ) : null}
        </CardContent>
      </Card>
    </main>
  );
}

function statusLabel(status: InvitationPreview["status"]): string {
  switch (status) {
    case "accepted":
      return "já aceito";
    case "expired":
      return "expirado";
    case "cancelled":
      return "cancelado";
    default:
      return status;
  }
}
