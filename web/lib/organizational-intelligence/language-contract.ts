import type { OrganizationalLearning } from "./organizational-learnings";

/**
 * Language Contract (TIP-012 §05, Founder) -- único ponto do código que
 * monta a frase executiva de um Aprendizado Organizacional. Usa
 * exclusivamente o vocabulário permitido; nenhum outro lugar do código
 * concatena texto para esta Capability. Preserva Executive Trust: nunca
 * um verbo de conclusão, nunca um adjetivo de gravidade (Architecture
 * Review §3.2).
 */
export function describeLearning(learning: OrganizationalLearning): string {
  const subject = learning.category === "risco" ? "Este risco" : "Esta ação";
  const verb = learning.category === "risco" ? "apareceu em" : "foi registrada em";
  return `${subject} ${verb} ${learning.occurrences} projetos diferentes.`;
}

/**
 * Vocabulário proibido (Architecture Review §3.2, ampliado no TIP-012
 * §05) -- usado apenas pelo teste que varre a redação renderizada desta
 * Capability. Nunca editado sem passar por uma nova Architecture Review.
 */
export const FORBIDDEN_VOCABULARY = [
  "revela",
  "demonstra",
  "indica",
  "significa",
  "prova",
  "causado por",
  "crítico",
  "crítica",
  "críticos",
  "críticas",
  "sistêmico",
  "sistêmica",
  "grave",
  "graves",
  "preocupante",
  "preocupantes",
  "alarmante",
  "alarmantes",
  "significativo",
  "significativa",
] as const;
