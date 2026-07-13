"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ActionsContextLine } from "@/components/workspace/actions-context-line";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";
import {
  NEXT_STEP_FALLBACK_MEETING,
  impactHeadline,
  suggestedNextStep,
} from "@/lib/workspace/meeting-momentum";
import { hasMeetingShape, type MeetingModelOutput } from "@/lib/workspace/types";

/**
 * Seção "Comunicação" (Executive Brief + Decision Momentum, FS-006 §2.4).
 * Substitui Ações + Decisões: um único bloco seguindo a Hierarquia
 * Executiva aprovada na User Journey -- Impacto, O que mudou, Pontos de
 * atenção, Decisões tomadas, Responsabilidades, Dependências, Próximo
 * passo. Painel C ("meeting"), independente das demais seções.
 *
 * meeting_intelligence não tem equivalente a health_status -- "Impacto da
 * reunião" é uma contagem real (impactHeadline), nunca uma nota de
 * severidade inventada.
 */
export function CommunicationBrief({ projectName }: { projectName: string }) {
  const latestMeeting = useWorkspaceLatestByKind(projectName, "meeting");

  return (
    <section className="flex flex-col gap-3" aria-labelledby="communication-heading">
      <h2 id="communication-heading" className="text-sm font-semibold text-ink-muted">
        Comunicação
      </h2>
      <Card>
        <CardContent className="flex flex-col gap-5 p-5">
          <ActionsContextLine projectName={projectName} />
          {latestMeeting.isPending ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : latestMeeting.isError ? (
            <p className="text-sm text-danger">Não foi possível carregar a comunicação do projeto.</p>
          ) : !latestMeeting.data ? (
            <p className="text-sm text-ink-muted">Nenhuma análise de reunião registrada ainda.</p>
          ) : !hasMeetingShape(latestMeeting.data.payload.model_output) ? (
            <p className="text-sm text-ink-muted">Resposta da IA não estruturada nesta análise.</p>
          ) : (
            <CommunicationBriefBody modelOutput={latestMeeting.data.payload.model_output} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function CommunicationBriefBody({ modelOutput }: { modelOutput: MeetingModelOutput }) {
  const nextStep = suggestedNextStep(modelOutput.issues.length, modelOutput.decisions.length);

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm font-medium text-ink">
        {impactHeadline(
          modelOutput.decisions.length,
          modelOutput.issues.length,
          modelOutput.action_items.length,
        )}
      </p>

      <div className="flex flex-col gap-2 border-t border-border pt-5">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">O que mudou</p>
        <p className="text-sm text-ink">{modelOutput.summary}</p>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Pontos de atenção</p>
        {modelOutput.issues.length === 0 ? (
          <p className="text-sm text-ink-muted">Nenhum ponto de atenção registrado nesta reunião.</p>
        ) : (
          <ul className="list-disc pl-5 text-sm">
            {modelOutput.issues.map((issue, index) => (
              <li key={index}>{issue}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Decisões tomadas</p>
          {modelOutput.decisions.length === 0 ? (
            <p className="text-sm text-ink-muted">Nenhuma decisão registrada.</p>
          ) : (
            <ul className="list-disc pl-5 text-sm">
              {modelOutput.decisions.map((decision, index) => (
                <li key={index}>{decision}</li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Dependências</p>
          {modelOutput.dependencies.length === 0 ? (
            <p className="text-sm text-ink-muted">Nenhuma dependência registrada.</p>
          ) : (
            <ul className="list-disc pl-5 text-sm">
              {modelOutput.dependencies.map((dependency, index) => (
                <li key={index}>{dependency}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Responsabilidades</p>
        {modelOutput.action_items.length === 0 ? (
          <p className="text-sm text-ink-muted">Nenhuma responsabilidade definida nesta reunião.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {modelOutput.action_items.map((item, index) => (
              <li key={index}>
                <Card>
                  <CardContent className="flex flex-col gap-1 p-4">
                    <p className="text-sm">{item.description}</p>
                    <div className="flex flex-wrap gap-4 text-xs text-ink-muted">
                      <span>Responsável: {item.owner ?? "Não definido"}</span>
                      <span>Prazo: {item.due_date ?? "Não definido"}</span>
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-col gap-1 rounded-md bg-surface-2 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Próximo passo</p>
        <p className="text-sm text-ink">{nextStep?.label ?? NEXT_STEP_FALLBACK_MEETING}</p>
      </div>
    </div>
  );
}
