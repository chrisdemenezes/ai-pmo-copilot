import { useMutation } from "@tanstack/react-query";

import type { RiskAdvisorAnswer } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function askRiskAdvisor(projectName: string, question: string): Promise<RiskAdvisorAnswer> {
  const response = await fetch(
    `/api/bff/workspace/${encodeURIComponent(projectName)}/risk-advisor`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
  );
  return parseWorkspaceResponse<RiskAdvisorAnswer>(response);
}

/**
 * Risk Advisor (Epic W3-3) -- read-only synthesis over risks already
 * identified, never a new analysis. No query invalidation on success: this
 * mutation never writes to any data the other Workspace panels read.
 */
export function useAskRiskAdvisor(projectName: string) {
  return useMutation({
    mutationFn: (question: string) => askRiskAdvisor(projectName, question),
  });
}
