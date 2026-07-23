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
 * invalidations, just the "risk" latest-by-kind instead of "status" --
 * never the other kinds' latest queries. workspace-recent added in TIP-011
 * (Executive Memory) for the same reason as useSubmitProjectStatus: without
 * it, the Reapareceu Insight would stay stale after a new risk analysis.
 *
 * TD-004: `cancelQueries` runs before `invalidateQueries` on the
 * "workspace-latest"/"workspace-recent" keys because the Riscos panel's
 * very first fetch for those keys can still be in flight when this
 * `onSuccess` fires. React Query only refetches a query whose fetchStatus
 * is idle -- an in-flight fetch just gets its existing promise returned,
 * so the invalidation is silently swallowed once that stale promise
 * resolves. Cancelling first forces the fetch back to idle.
 */
export function useSubmitRiskReview(projectName: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectContext: string) => submitRiskReview(projectName, projectContext),
    onSuccess: async () => {
      await queryClient.cancelQueries({ queryKey: ["workspace-latest", projectName, "risk"] });
      await queryClient.cancelQueries({ queryKey: ["workspace-recent", projectName, "risk"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-summary", projectName] });
      queryClient.invalidateQueries({ queryKey: ["workspace-latest", projectName, "risk"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-recent", projectName, "risk"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-timeline", projectName] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
    },
  });
}
