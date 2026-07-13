import { describe, expect, it } from "vitest";

import {
  URGENCY_ORDER,
  attentionHeadline,
  bucketByUrgency,
  suggestedNextAction,
  urgencyLabel,
} from "./action-momentum";
import type { ActionItemView } from "./types";

const TODAY = new Date("2026-07-13T12:00:00Z");

function item(overrides: Partial<ActionItemView>): ActionItemView {
  return {
    project_name: "Aurora",
    description: "Atualizar cronograma",
    owner: "Ana",
    due_date: null,
    source_analysis_id: 1,
    source_created_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

describe("bucketByUrgency", () => {
  it("returns 'atrasado' for a due date in the past", () => {
    expect(bucketByUrgency("2026-07-10", TODAY)).toBe("atrasado");
  });

  it("returns 'vence_em_breve' for a due date within the next 7 days", () => {
    expect(bucketByUrgency("2026-07-18", TODAY)).toBe("vence_em_breve");
  });

  // Boundary the FS calls out explicitly ("incluindo data-limite exata"):
  // exactly 7 days ahead still counts as due soon, not on track.
  it("returns 'vence_em_breve' at exactly the 7-day boundary", () => {
    expect(bucketByUrgency("2026-07-20T12:00:00Z", TODAY)).toBe("vence_em_breve");
  });

  it("returns 'no_prazo' for a due date beyond 7 days", () => {
    expect(bucketByUrgency("2026-08-01", TODAY)).toBe("no_prazo");
  });

  it("returns 'sem_prazo' when there is no due date", () => {
    expect(bucketByUrgency(null, TODAY)).toBe("sem_prazo");
  });

  // Real risk from FS-007 §11: due_date is free text extracted by the AI --
  // an unparseable value degrades to "sem_prazo", never breaks the screen.
  it("returns 'sem_prazo' for free-text due dates the AI failed to normalize", () => {
    expect(bucketByUrgency("assim que possível", TODAY)).toBe("sem_prazo");
    expect(bucketByUrgency("", TODAY)).toBe("sem_prazo");
  });
});

describe("attentionHeadline", () => {
  it("renders the two real counts, never an invented score", () => {
    expect(attentionHeadline(3, 2)).toBe("3 atrasada(s) · 2 vence(m) em breve");
    expect(attentionHeadline(0, 0)).toBe("0 atrasada(s) · 0 vence(m) em breve");
  });
});

describe("suggestedNextAction", () => {
  it("returns null for an empty list", () => {
    expect(suggestedNextAction([])).toBeNull();
  });

  it("returns null when no item has a parseable due date", () => {
    const items = [item({ due_date: null }), item({ due_date: "sem data definida" })];
    expect(suggestedNextAction(items)).toBeNull();
  });

  it("picks the item overdue the longest among multiple overdue items", () => {
    const oldest = item({ description: "mais antiga", due_date: "2026-07-01" });
    const items = [
      item({ description: "recente", due_date: "2026-07-12" }),
      oldest,
      item({ description: "futura", due_date: "2026-07-25" }),
    ];
    expect(suggestedNextAction(items)).toBe(oldest);
  });

  it("picks the nearest deadline when nothing is overdue", () => {
    const nearest = item({ description: "mais próxima", due_date: "2026-07-15" });
    const items = [item({ description: "distante", due_date: "2026-08-10" }), nearest];
    expect(suggestedNextAction(items)).toBe(nearest);
  });

  it("skips unparseable due dates without discarding the rest", () => {
    const valid = item({ description: "válida", due_date: "2026-07-16" });
    const items = [item({ due_date: "texto livre" }), valid];
    expect(suggestedNextAction(items)).toBe(valid);
  });
});

describe("urgency rendering rules", () => {
  it("keeps 'atrasado' always first in the fixed order", () => {
    expect(URGENCY_ORDER[0]).toBe("atrasado");
    expect(URGENCY_ORDER).toHaveLength(4);
  });

  it("labels every bucket in Portuguese", () => {
    expect(urgencyLabel("atrasado")).toBe("Atrasado");
    expect(urgencyLabel("vence_em_breve")).toBe("Vence em breve");
    expect(urgencyLabel("no_prazo")).toBe("No prazo");
    expect(urgencyLabel("sem_prazo")).toBe("Sem prazo");
  });
});
