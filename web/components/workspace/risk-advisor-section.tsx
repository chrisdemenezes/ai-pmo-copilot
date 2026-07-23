"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAskRiskAdvisor } from "@/lib/hooks/use-ask-risk-advisor";

const MIN_LENGTH = 3;

/**
 * Risk Advisor (Epic W3-3) -- camada conversacional somente leitura sobre os
 * riscos já identificados (Domain Blueprint §1/§6). Nunca dispara uma nova
 * análise; cada pergunta é independente, sem histórico de conversa
 * persistido (Blueprint §13/§14).
 */
export function RiskAdvisorSection({ projectName }: { projectName: string }) {
  const [question, setQuestion] = useState("");
  const mutation = useAskRiskAdvisor(projectName);

  function handleAsk() {
    if (question.trim().length < MIN_LENGTH) {
      return;
    }
    mutation.mutate(question, {
      onSuccess: () => setQuestion(""),
    });
  }

  return (
    <section className="flex flex-col gap-3" aria-labelledby="risk-advisor-heading">
      <h2 id="risk-advisor-heading" className="text-sm font-semibold text-ink-muted">
        Risk Advisor
      </h2>
      <Card>
        <CardContent className="flex flex-col gap-4 p-5">
          <p className="text-sm text-ink-muted">
            Pergunte sobre os riscos já identificados deste projeto -- por exemplo, &ldquo;qual o
            risco mais crítico agora?&rdquo;.
          </p>
          <Textarea
            aria-label="Pergunta para o Risk Advisor"
            placeholder="Digite sua pergunta..."
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            disabled={mutation.isPending}
          />
          <div>
            <Button
              onClick={handleAsk}
              disabled={mutation.isPending || question.trim().length < MIN_LENGTH}
            >
              {mutation.isPending ? "Perguntando..." : "Perguntar"}
            </Button>
          </div>

          {mutation.isError ? (
            <p className="text-sm text-danger">
              {mutation.error instanceof Error
                ? mutation.error.message
                : "Não foi possível obter uma resposta."}
            </p>
          ) : null}

          {mutation.isSuccess ? (
            <div className="flex flex-col gap-2 rounded-md bg-surface-2 p-4">
              <p className="text-sm text-ink">{mutation.data.answer}</p>
              {mutation.data.cited_analyses.length > 0 ? (
                <div className="flex flex-col gap-1">
                  <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                    Baseado em
                  </p>
                  <ul className="flex flex-wrap gap-2 text-xs text-ink-muted">
                    {mutation.data.cited_analyses.map((citation) => (
                      <li key={citation.source_analysis_id}>
                        Análise de {new Date(citation.source_created_at).toLocaleDateString("pt-BR")}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
