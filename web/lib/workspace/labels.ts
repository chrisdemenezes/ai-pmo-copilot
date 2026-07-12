import type { AnalysisListItem } from "./types";

const KIND_LABEL: Record<AnalysisListItem["kind"], string> = {
  meeting: "Reunião",
  risk: "Risco",
  status: "Status",
};

export function analysisKindLabel(kind: AnalysisListItem["kind"]): string {
  return KIND_LABEL[kind];
}

const SEVERITY_LABEL: Record<"low" | "medium" | "high", string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
};

export function severityLabel(level: "low" | "medium" | "high"): string {
  return SEVERITY_LABEL[level];
}
