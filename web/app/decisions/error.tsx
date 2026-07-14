"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DashboardFetchError } from "@/lib/hooks/use-portfolio-summary";

export default function DecisionsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const detail = error instanceof DashboardFetchError ? error.body.detail : undefined;

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
          <p className="text-lg font-medium">Não foi possível carregar as decisões agora</p>
          <p className="text-sm text-ink-muted">
            Tente novamente em instantes. Se o problema persistir, informe o código de referência
            ao suporte.
          </p>
          {detail && <p className="font-mono text-xs text-ink-faint">{detail}</p>}
          <Button onClick={() => reset()}>Tentar novamente</Button>
        </CardContent>
      </Card>
    </main>
  );
}
