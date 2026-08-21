import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { describeLearning } from "@/lib/organizational-intelligence/language-contract";
import type { OrganizationalLearning } from "@/lib/organizational-intelligence/organizational-learnings";

/**
 * Card de Aprendizado Organizacional (FS-011 §3.5, TIP-012 §07) -- Zero
 * Labels Rule (FS-011 §5): nenhum rótulo/chip de conceito, o cabeçalho de
 * categoria já dá o contexto. 3 linhas: frase executiva (Language
 * Contract), texto verbatim, projetos reais navegáveis (auditabilidade).
 *
 * V1 Product & Capability Completion, Pacote F: a recorrência
 * (learning.occurrences) já existia embutida na frase executiva, mas só
 * como prosa -- sem nenhum elemento visual permitindo escanear rápido a
 * lista. O selo "Nx" reaproveita o mesmo dado, não uma contagem nova
 * (Zero Labels Rule preservada -- não é um rótulo de conceito, é a
 * contagem já dita na frase, só destacada). Citação e projetos ganham
 * hierarquia visual (borda esquerda / rótulo "Projetos"), sem alterar
 * nenhum texto ou dado.
 */
export function OrganizationalLearningCard({ learning }: { learning: OrganizationalLearning }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm font-medium text-ink">{describeLearning(learning)}</p>
          <Badge variant="neutral" className="shrink-0">
            {learning.occurrences}x
          </Badge>
        </div>
        <p className="border-l-2 border-border-strong pl-3 text-sm italic text-ink-muted">
          &quot;{learning.description}&quot;
        </p>
        <p className="flex flex-wrap items-baseline gap-x-1 text-xs text-ink-faint">
          <span className="font-medium uppercase tracking-wide">Projetos:</span>
          {learning.projectNames.map((projectName, index) => (
            <span key={projectName}>
              <Link
                href={`/workspace/${encodeURIComponent(projectName)}`}
                className="hover:text-accent hover:underline"
              >
                {projectName}
              </Link>
              {index < learning.projectNames.length - 1 ? " · " : null}
            </span>
          ))}
        </p>
      </CardContent>
    </Card>
  );
}
