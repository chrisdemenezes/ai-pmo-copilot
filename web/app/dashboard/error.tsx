"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { DashboardFetchError } from "@/lib/hooks/use-portfolio-summary";

export default function DashboardError({
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
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center gap-3 p-12 text-center">
      <p className="text-lg font-medium">Não foi possível carregar o portfólio agora</p>
      <p className="text-sm text-ink-muted">
        Tente novamente em instantes. Se o problema persistir, informe o código de referência ao
        suporte.
      </p>
      {detail && <p className="font-mono text-xs text-ink-faint">{detail}</p>}
      <Button onClick={() => reset()}>Tentar novamente</Button>
    </main>
  );
}
