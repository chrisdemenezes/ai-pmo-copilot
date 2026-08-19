import { describe, expect, it } from "vitest";

import { computeExecutiveFocus } from "./executive-focus";
import type { ProjectIntelligenceSummary } from "@/lib/project/intelligence-summary";

describe("computeExecutiveFocus", () => {
  it("picks the project with the most open risks", () => {
    const projects: ProjectIntelligenceSummary[] = [
      { project_name: "Aurora", project_id: 1, total_analyses: 2, open_risks: 1, pending_action_items: 0, latest_health_status: "green" },
      { project_name: "Multilift", project_id: 1, total_analyses: 5, open_risks: 3, pending_action_items: 2, latest_health_status: "red" },
    ];
    const focus = computeExecutiveFocus(projects);
    expect(focus?.title).toBe("Multilift");
    expect(focus?.reason).toContain("3 riscos");
    expect(focus?.href).toBe("/workspace/Multilift");
  });

  it("uses singular wording for exactly one open risk", () => {
    const projects: ProjectIntelligenceSummary[] = [
      { project_name: "Aurora", project_id: 1, total_analyses: 2, open_risks: 1, pending_action_items: 0, latest_health_status: "yellow" },
    ];
    const focus = computeExecutiveFocus(projects);
    expect(focus?.reason).toContain("1 risco identificado");
  });

  it("falls back to a project with red health when no risks are open", () => {
    const projects: ProjectIntelligenceSummary[] = [
      { project_name: "Zephyr", project_id: 1, total_analyses: 1, open_risks: 0, pending_action_items: 0, latest_health_status: "red" },
      { project_name: "Aurora", project_id: 1, total_analyses: 2, open_risks: 0, pending_action_items: 0, latest_health_status: "green" },
    ];
    const focus = computeExecutiveFocus(projects);
    expect(focus?.title).toBe("Zephyr");
    expect(focus?.reason).toContain("crítico");
  });

  it("returns null when there is nothing critical to focus on", () => {
    const projects: ProjectIntelligenceSummary[] = [
      { project_name: "Aurora", project_id: 1, total_analyses: 2, open_risks: 0, pending_action_items: 0, latest_health_status: "green" },
    ];
    expect(computeExecutiveFocus(projects)).toBeNull();
  });

  it("returns null for an empty portfolio", () => {
    expect(computeExecutiveFocus([])).toBeNull();
  });

  it("encodes project names with special characters in the href", () => {
    const projects: ProjectIntelligenceSummary[] = [
      { project_name: "Implantacao SAP S/4HANA", project_id: 1, total_analyses: 2, open_risks: 1, pending_action_items: 1, latest_health_status: "yellow" },
    ];
    const focus = computeExecutiveFocus(projects);
    expect(focus?.href).toBe("/workspace/Implantacao%20SAP%20S%2F4HANA");
  });
});
