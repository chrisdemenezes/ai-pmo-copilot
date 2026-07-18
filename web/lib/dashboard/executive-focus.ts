import { rankByRisk } from "./aggregate";
import type { ProjectSummary } from "./types";

export interface ExecutiveFocusItem {
  title: string;
  subtitle: string;
  reason: string;
  href: string;
}

/**
 * Entrega 2.4 -- "Onde devo concentrar minha atenção hoje?" Calculado a
 * partir de dado real (mesmo rankByRisk() já usado pelo Risk Concentration
 * Ranking, W5) -- não é um item mock. Fallback para o primeiro projeto com
 * saúde crítica quando nenhum risco está aberto.
 */
export function computeExecutiveFocus(projects: ProjectSummary[]): ExecutiveFocusItem | null {
  const [riskiest] = rankByRisk(projects, 1);
  if (riskiest) {
    return {
      title: riskiest.project_name,
      subtitle: "Projeto crítico",
      reason: `Maior concentração de riscos do portfólio (${riskiest.open_risks} risco${riskiest.open_risks === 1 ? "" : "s"} identificado${riskiest.open_risks === 1 ? "" : "s"}).`,
      href: `/workspace/${encodeURIComponent(riskiest.project_name)}`,
    };
  }

  const critical = projects.find((project) => project.latest_health_status === "red");
  if (critical) {
    return {
      title: critical.project_name,
      subtitle: "Projeto crítico",
      reason: "Status de saúde crítico na análise mais recente.",
      href: `/workspace/${encodeURIComponent(critical.project_name)}`,
    };
  }

  return null;
}
