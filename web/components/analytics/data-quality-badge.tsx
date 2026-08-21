import { Info } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { metricReasonLabel } from "@/lib/domain/executive-metric";

/**
 * Wave 8 (Executive Analytics) -- shown next to any metric that has no
 * value, explaining exactly why (never a silent "—" with no explanation).
 * Same Info+Tooltip pattern already established by
 * `cockpit/portfolio-situation-grid.tsx` (Package G, Health x Schedule).
 */
export function DataQualityBadge({ reason }: { reason: string }) {
  return (
    <Tooltip>
      <TooltipTrigger aria-label="Por que este dado não está disponível?">
        <Info className="size-3.5 text-ink-faint" aria-hidden="true" />
      </TooltipTrigger>
      <TooltipContent>
        <p className="max-w-56 text-xs">{metricReasonLabel(reason)}</p>
      </TooltipContent>
    </Tooltip>
  );
}
