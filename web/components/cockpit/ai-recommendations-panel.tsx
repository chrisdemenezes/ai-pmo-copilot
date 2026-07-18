import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { AIRecommendation } from "@/lib/mock/cockpit-data";

/**
 * Entrega 2.4 -- AI Recommendations (dados simulados). Representa a
 * camada de inteligência futura da STRATECH (Release 0.3+, contrato
 * formal de Accelerator) -- nenhum agente real gera estas recomendações
 * ainda, diferente dos 3 Accelerators reais já em produção (V1).
 */
export function AIRecommendationsPanel({
  recommendations,
}: {
  recommendations: AIRecommendation[];
}) {
  return (
    <Card className="border-accent-soft">
      <CardContent className="flex flex-col gap-3 p-5">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-accent" aria-hidden="true" />
          <p className="font-display text-sm font-semibold text-ink">A IA recomenda</p>
        </div>
        <ul className="flex flex-col gap-2">
          {recommendations.map((recommendation) => (
            <li key={recommendation.text} className="flex items-start gap-2 text-sm">
              <Badge variant="outline">{recommendation.category}</Badge>
              <span className="text-ink">{recommendation.text}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
