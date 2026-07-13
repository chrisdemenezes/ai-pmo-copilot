import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { AnalyzeMeetingIntelligenceResponse } from "@/lib/workspace/types";
import { parseWorkspaceResponse } from "./workspace-fetch-error";

async function submitMeetingIntelligence(
  projectName: string,
  projectContext: string,
): Promise<AnalyzeMeetingIntelligenceResponse> {
  const response = await fetch(
    `/api/bff/workspace/${encodeURIComponent(projectName)}/analyze/meeting`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_context: projectContext }),
    },
  );
  return parseWorkspaceResponse<AnalyzeMeetingIntelligenceResponse>(response);
}

/**
 * Same template as useSubmitProjectStatus / useSubmitRiskReview (FS-005 §3,
 * FS-006 §3): the same 4 invalidations, "meeting" as the latest-by-kind --
 * never the other 2 kinds' latest queries.
 */
export function useSubmitMeetingIntelligence(projectName: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectContext: string) => submitMeetingIntelligence(projectName, projectContext),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace-summary", projectName] });
      queryClient.invalidateQueries({ queryKey: ["workspace-latest", projectName, "meeting"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-timeline", projectName] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
    },
  });
}
