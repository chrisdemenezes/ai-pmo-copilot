import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "./navigation";

describe("NAV_ITEMS", () => {
  it("contains exactly fifteen entries -- the only fully real modules today (Capability 03, User Management, API Keys, Sessions, Invitations, Document Ingestion, Mission Control, Executive Intelligence)", () => {
    expect(NAV_ITEMS).toHaveLength(15);
  });

  it("points the first entry at the real Dashboard route", () => {
    expect(NAV_ITEMS[0].href).toBe("/dashboard");
    expect(NAV_ITEMS[0].label).toBe("Dashboard");
  });

  it("points the second entry at the real Priorização (Portfolio Intelligence) route", () => {
    expect(NAV_ITEMS[1].href).toBe("/portfolio");
    expect(NAV_ITEMS[1].label).toBe("Priorização");
  });

  it("points the third entry at the real Projetos route", () => {
    expect(NAV_ITEMS[2].href).toBe("/projects");
    expect(NAV_ITEMS[2].label).toBe("Projetos");
  });

  it("points the fourth entry at the real Program Management route", () => {
    expect(NAV_ITEMS[3].href).toBe("/program-management");
    expect(NAV_ITEMS[3].label).toBe("Program Management");
  });

  it("points the fifth entry at the real Project Delivery route", () => {
    expect(NAV_ITEMS[4].href).toBe("/project-delivery");
    expect(NAV_ITEMS[4].label).toBe("Project Delivery");
  });

  it("points the sixth entry at the real Ações route", () => {
    expect(NAV_ITEMS[5].href).toBe("/actions");
    expect(NAV_ITEMS[5].label).toBe("Ações");
  });

  it("points the seventh entry at the real Decisões route", () => {
    expect(NAV_ITEMS[6].href).toBe("/decisions");
    expect(NAV_ITEMS[6].label).toBe("Decisões");
  });

  it("points the eighth entry at the real Inteligência Executiva route (V1 Product & Capability Completion, Pacote A)", () => {
    expect(NAV_ITEMS[7].href).toBe("/inteligencia-executiva");
    expect(NAV_ITEMS[7].label).toBe("Inteligência Executiva");
  });

  it("points the ninth entry at the real Aprendizados (Organizational Intelligence) route", () => {
    expect(NAV_ITEMS[8].href).toBe("/aprendizados");
    expect(NAV_ITEMS[8].label).toBe("Aprendizados");
  });

  it("points the tenth entry at the real Administração (User Management) route", () => {
    expect(NAV_ITEMS[9].href).toBe("/administracao/usuarios");
    expect(NAV_ITEMS[9].label).toBe("Administração");
  });

  it("points the eleventh entry at the real Chaves de API (API Keys, D-051) route", () => {
    expect(NAV_ITEMS[10].href).toBe("/administracao/api-keys");
    expect(NAV_ITEMS[10].label).toBe("Chaves de API");
  });

  it("points the twelfth entry at the real Sessões (server-side sessions, TD-010) route", () => {
    expect(NAV_ITEMS[11].href).toBe("/administracao/sessoes");
    expect(NAV_ITEMS[11].label).toBe("Sessões");
  });

  it("points the thirteenth entry at the real Convites (Invitations, D-054) route", () => {
    expect(NAV_ITEMS[12].href).toBe("/administracao/convites");
    expect(NAV_ITEMS[12].label).toBe("Convites");
  });

  it("points the fourteenth entry at the real Documentos (Document Ingestion, W5-0) route", () => {
    expect(NAV_ITEMS[13].href).toBe("/administracao/documentos");
    expect(NAV_ITEMS[13].label).toBe("Documentos");
  });

  it("points the fifteenth entry at Mission Control", () => {
    expect(NAV_ITEMS[14].href).toBe("/mission-control");
    expect(NAV_ITEMS[14].label).toBe("Mission Control");
  });

  // V1 Product & Capability Completion, Pacote B: Priorização/Projetos/
  // Program Management/Project Delivery share the same visual group,
  // consecutively, and nothing else does.
  it("groups Priorização/Projetos/Program Management/Project Delivery under the same 'Execução' group, consecutively", () => {
    const executionItems = NAV_ITEMS.filter((item) => item.group === "Execução");
    expect(executionItems.map((item) => item.label)).toEqual([
      "Priorização",
      "Projetos",
      "Program Management",
      "Project Delivery",
    ]);
    const indices = executionItems.map((item) => NAV_ITEMS.indexOf(item));
    expect(indices).toEqual([1, 2, 3, 4]);
  });

  it("does not assign a group to any other entry", () => {
    const ungrouped = NAV_ITEMS.filter((item) => item.group === undefined);
    expect(ungrouped).toHaveLength(11);
  });
});
