"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function EntrarForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Demo Mode (STRATECH V2 Epic 2 / EO-015): pre-fills organization + e-mail
  // as a convenience, never as a bypass -- both fields stay editable and
  // login still goes through the real, organization-scoped authentication
  // flow (POST /api/bff/session). There is no subdomain-based organization
  // resolution yet, so the field is always part of the form.
  const isDemo = searchParams.get("demo") === "1";
  const [organization, setOrganization] = useState(isDemo ? "demo-organization" : "");
  const [email, setEmail] = useState(isDemo ? "demo@stratech.local" : "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);

    const response = await fetch("/api/bff/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ organization, email, password }),
    });

    if (!response.ok) {
      setPending(false);
      setError("Organização, e-mail ou senha incorretos. Tente novamente.");
      return;
    }

    const redirectTo = searchParams.get("redirect") ?? "/dashboard";
    router.push(redirectTo);
    router.refresh();
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Entrar na STRATECH</CardTitle>
        <CardDescription>Autenticação individual.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="organization">Organização</Label>
            <Input
              id="organization"
              name="organization"
              type="text"
              value={organization}
              onChange={(event) => setOrganization(event.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">E-mail</Label>
            <Input
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="password">Senha</Label>
            <Input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
          <Button type="submit" disabled={pending}>
            {pending ? "Entrando…" : "Entrar"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function EntrarPage() {
  return (
    <main className="flex min-h-full flex-1 items-center justify-center p-6">
      <Suspense fallback={null}>
        <EntrarForm />
      </Suspense>
    </main>
  );
}
