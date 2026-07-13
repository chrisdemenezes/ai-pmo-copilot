import { WorkspaceHeader } from "@/components/workspace/workspace-header";
import { ExecutiveBrief } from "@/components/workspace/executive-brief";
import { IntelligenceTimeline } from "@/components/workspace/intelligence-timeline";
import { RisksPanel } from "@/components/workspace/risks-panel";
import { CommunicationBrief } from "@/components/workspace/communication-brief";
import { ActionsSection } from "@/components/workspace/actions-section";
import { AnalysisHistory } from "@/components/workspace/analysis-history";

/**
 * Rota dinâmica -- não representa uma entidade Project persistida (TIP-004,
 * decisão do Chief Product Architect). projectName decodificado
 * automaticamente pelo Next.js a partir do segmento de rota; cada seção
 * abaixo consome um dos 3 painéis independentes (A: summary, B: timeline,
 * C: latest-by-kind) via seus próprios hooks -- nenhuma seção bloqueia as
 * demais.
 */
export default async function WorkspacePage({
  params,
}: {
  params: Promise<{ projectName: string }>;
}) {
  // Next.js hands the raw (still URL-encoded) route segment here -- decode
  // once, at this single entry point, so every hook/BFF call below encodes
  // it exactly once instead of double-encoding (the "/" in real project
  // names like "Implantacao SAP S/4HANA" is exactly why this matters).
  const { projectName: rawProjectName } = await params;
  const projectName = decodeURIComponent(rawProjectName);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 p-6">
      <WorkspaceHeader projectName={projectName} />
      <ExecutiveBrief projectName={projectName} />
      <IntelligenceTimeline projectName={projectName} />
      <RisksPanel projectName={projectName} />
      <CommunicationBrief projectName={projectName} />
      <ActionsSection projectName={projectName} />
      <AnalysisHistory projectName={projectName} />
    </main>
  );
}
