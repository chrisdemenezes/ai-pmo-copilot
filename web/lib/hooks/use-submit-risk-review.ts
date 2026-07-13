import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { AnalyzeRiskReviewResponse } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function submitRiskReview(
  projectName: string,
  projectContext: string,
): Promise<AnalyzeRiskReviewResponse> {
  const response = await fetch(
    `/api/bff/workspace/${encodeURIComponent(projectName)}/analyze/risk`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_context: projectContext }),
    },
  );
  return parseWorkspaceResponse<AnalyzeRiskReviewResponse>(response);
}

/**
 * Same template as useSubmitProjectStatus (FS-005 §3 / TIP-005A): the same
 * 4 invalidations, just the "risk" latest-by-kind instead of "status" --
 * never the other kinds' latest queries.
 */
export function useSubmitRiskReview(projectName: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectContext: string) => submitRiskReview(projectName, projectContext),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace-summary", projectName] });
      queryClient.invalidateQueries({ queryKey: ["workspace-latest", projectName, "risk"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-timeline", projectName] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
    },
  });
}
