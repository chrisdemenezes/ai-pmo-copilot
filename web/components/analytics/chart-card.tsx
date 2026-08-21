import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Wave 8 (Executive Analytics) -- the shared shell every chart renders
 * inside: a Card with a title/description, and a mandatory explicit empty
 * state whenever the underlying data doesn't exist yet. No chart in this
 * product ever silently renders a fabricated/interpolated placeholder --
 * `isEmpty` must be set by the caller from real data availability, never
 * from a loading/error state alone.
 */
export function ChartCard({
  title,
  description,
  isEmpty,
  emptyMessage = "Dados insuficientes para esta visualização.",
  children,
}: {
  title: string;
  description?: string;
  isEmpty: boolean;
  emptyMessage?: string;
  children: ReactNode;
}) {
  return (
    <Card data-testid="chart-card">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="min-w-0">
        {isEmpty ? (
          <p className="py-8 text-center text-sm text-ink-faint">{emptyMessage}</p>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
