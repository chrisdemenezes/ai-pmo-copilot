import { describe, expect, it } from "vitest";

import { aggregatePortfolio, groupByHealthStatus, rankByRisk } from "./aggregate";
import type { ProjectSummary } from "./types";

const projects: ProjectSummary[] = [
  {
    project_name: "Multilift",
    total_analyses: 5,
    open_risks: 3,
    pending_action_items: 2,
    latest_health_status: "red",
  },
  {
    project_name: "Aurora",
    total_analyses: 2,
    open_risks: 0,
    pending_action_items: 1,
    latest_health_status: "green",
  },
  {
    project_name: "Zephyr",
    total_analyses: 1,
    open_risks: 1,
    pending_action_items: 0,
    latest_health_status: null,
  },
];

describe("aggregatePortfolio", () => {
  it("sums counts across all projects", () => {
    expect(aggregatePortfolio(projects)).toEqual({
      projectCount: 3,
      totalOpenRisks: 4,
      totalPendingActionItems: 3,
    });
  });

  it("returns zeros for an empty portfolio", () => {
    expect(aggregatePortfolio([])).toEqual({
      projectCount: 0,
      totalOpenRisks: 0,
      totalPendingActionItems: 0,
    });
  });
});

describe("groupByHealthStatus", () => {
  it("counts each real status plus null as none", () => {
    expect(groupByHealthStatus(projects)).toEqual({ green: 1, yellow: 0, red: 1, none: 1 });
  });
});

describe("rankByRisk", () => {
  it("excludes projects with zero open risks and sorts descending", () => {
    expect(rankByRisk(projects).map((p) => p.project_name)).toEqual(["Multilift", "Zephyr"]);
  });

  it("respects the limit", () => {
    expect(rankByRisk(projects, 1)).toHaveLength(1);
  });

  it("returns an empty list when no project has open risks", () => {
    const noRisk = projects.map((p) => ({ ...p, open_risks: 0 }));
    expect(rankByRisk(noRisk)).toEqual([]);
  });
});
