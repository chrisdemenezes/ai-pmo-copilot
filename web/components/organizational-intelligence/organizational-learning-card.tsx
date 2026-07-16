import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { describeLearning } from "@/lib/organizational-intelligence/language-contract";
import type { OrganizationalLearning } from "@/lib/organizational-intelligence/organizational-learnings";

/**
 * Card de Aprendizado Organizacional (FS-011 §3.5, TIP-012 §07) -- Zero
 * Labels Rule (FS-011 §5): nenhum rótulo/chip de conceito, o cabeçalho de
 * categoria já dá o contexto. 3 linhas: frase executiva (Language
 * Contract), texto verbatim, projetos reais navegáveis (auditabilidade).
 */
export function OrganizationalLearningCard({ learning }: { learning: OrganizationalLearning }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-2 p-5">
        <p className="text-sm font-medium text-ink">{describeLearning(learning)}</p>
        <p className="text-sm text-ink-muted">&quot;{learning.description}&quot;</p>
        <p className="flex flex-wrap gap-x-1 text-xs text-ink-faint">
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
