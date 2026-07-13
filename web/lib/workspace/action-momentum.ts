import type { ActionItemView } from "./types";

/**
 * Decision Momentum for Action Intelligence (FS-007 §2.4) -- same principle
 * as meeting-momentum.ts / risk-momentum.ts: every function here is a fixed
 * UI rule over real fields (due_date, real counts), never an invented
 * severity score and never an AI claim. The three fixed executive questions
 * ("O que está atrasado?" → "O que vence em seguida?" → "O que exige minha
 * atenção hoje?") are answered by visual hierarchy computed here, never by
 * user-configurable filters or views.
 */

/** Always derived from due_date at render time -- never persisted (FS-007 §2.6). */
export type UrgencyBucket = "atrasado" | "vence_em_breve" | "no_prazo" | "sem_prazo";

/**
 * Future, when persistence arrives (FS-007 §2.6): ActionStatus will coexist
 * with UrgencyBucket in the same single visual "estado do item" slot the
 * card already renders. Declared as the contract the write Feature must
 * honor -- deliberately never read nor written anywhere in this delivery.
 */
export type ActionStatus = "aberto" | "em_andamento" | "concluido" | "delegado";

const SOON_WINDOW_DAYS = 7;

function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

/**
 * due_date is free text extracted by the AI (FS-007 §11) -- an unparseable
 * value must degrade to "no deadline", never break the screen.
 */
function parseDueDate(dueDate: string | null): Date | null {
  if (!dueDate) return null;
  const due = new Date(dueDate);
  return Number.isNaN(due.getTime()) ? null : due;
}

export function bucketByUrgency(dueDate: string | null, today: Date): UrgencyBucket {
  const due = parseDueDate(dueDate);
  if (!due) return "sem_prazo";
  if (due < today) return "atrasado";
  if (due <= addDays(today, SOON_WINDOW_DAYS)) return "vence_em_breve";
  return "no_prazo";
}

/**
 * "O que exige minha atenção hoje?" -- never an invented severity note,
 * same honesty as impactHeadline() in meeting-momentum.ts: only real counts.
 */
export function attentionHeadline(atrasadoCount: number, venceEmBreveCount: number): string {
  return `${atrasadoCount} atrasada(s) · ${venceEmBreveCount} vence(m) em breve`;
}

/**
 * The single most urgent item -- overdue the longest, or with the nearest
 * deadline. The two rules collapse into one honest comparison: the earliest
 * parseable due_date is the most urgent, whether it is already past or not.
 * Rendered as text, never a clickable CTA (same principle as the 3 Briefs).
 * Returns null -- never a fabricated suggestion -- when no item has a
 * parseable deadline.
 */
export function suggestedNextAction(items: ActionItemView[]): ActionItemView | null {
  let mostUrgent: ActionItemView | null = null;
  let mostUrgentDue: Date | null = null;

  for (const item of items) {
    const due = parseDueDate(item.due_date);
    if (!due) continue;
    if (!mostUrgentDue || due < mostUrgentDue) {
      mostUrgent = item;
      mostUrgentDue = due;
    }
  }

  return mostUrgent;
}

/** Fixed rendering order -- "atrasado sempre primeiro" (FS-007 §09). */
export const URGENCY_ORDER: readonly UrgencyBucket[] = [
  "atrasado",
  "vence_em_breve",
  "no_prazo",
  "sem_prazo",
];

const URGENCY_LABEL: Record<UrgencyBucket, string> = {
  atrasado: "Atrasado",
  vence_em_breve: "Vence em breve",
  no_prazo: "No prazo",
  sem_prazo: "Sem prazo",
};

export function urgencyLabel(bucket: UrgencyBucket): string {
  return URGENCY_LABEL[bucket];
}
