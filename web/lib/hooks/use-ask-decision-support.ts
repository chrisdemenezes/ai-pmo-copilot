import { useMutation } from "@tanstack/react-query";

import type { DashboardErrorBody, DecisionSupportResponse, DecisionSupportScope } from "@/lib/dashboard/types";

export class DecisionSupportFetchError extends Error {
  constructor(public readonly body: DashboardErrorBody) {
    super(body.detail);
  }
}

async function askDecisionSupport(
  question: string,
  scope: DecisionSupportScope,
): Promise<DecisionSupportResponse> {
  const response = await fetch("/api/bff/decision-support", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, scope }),
  });
  const body = await response.json();
  if (!response.ok) {
    throw new DecisionSupportFetchError(body as DashboardErrorBody);
  }
  return body as DecisionSupportResponse;
}

/**
 * Decision Support (Wave 6) -- the first functional Executive Intelligence
 * Capability with a real HTTP consumer. Read-only synthesis over
 * Explanations already produced by the selected Advisors, never a new
 * analysis -- no query invalidation on success.
 */
export function useAskDecisionSupport() {
  return useMutation({
    mutationFn: ({ question, scope }: { question: string; scope: DecisionSupportScope }) =>
      askDecisionSupport(question, scope),
  });
}
