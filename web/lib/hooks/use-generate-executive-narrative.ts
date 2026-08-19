import { useMutation } from "@tanstack/react-query";

import type {
  DashboardErrorBody,
  DecisionSupportScope,
  ExecutiveNarrativeResponse,
} from "@/lib/dashboard/types";

export class ExecutiveNarrativeFetchError extends Error {
  constructor(public readonly body: DashboardErrorBody) {
    super(body.detail);
  }
}

async function generateExecutiveNarrative(
  scope: DecisionSupportScope,
): Promise<ExecutiveNarrativeResponse> {
  const response = await fetch("/api/bff/executive-narrative", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scope }),
  });
  const body = await response.json();
  if (!response.ok) {
    throw new ExecutiveNarrativeFetchError(body as DashboardErrorBody);
  }
  return body as ExecutiveNarrativeResponse;
}

/**
 * Executive Narrative (Wave 6) -- second functional Executive Intelligence
 * Capability with a real HTTP consumer. Never accepts a free-text question
 * -- only `scope` (Technical Design §2/§5.2). Read-only synthesis over
 * Explanations already produced by the selected Advisors, never a new
 * analysis -- no query invalidation on success.
 */
export function useGenerateExecutiveNarrative() {
  return useMutation({
    mutationFn: (scope: DecisionSupportScope) => generateExecutiveNarrative(scope),
  });
}
