import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { WorkspaceHeader } from "./workspace-header";
import { ExecutiveBrief } from "./executive-brief";
import { IntelligenceTimeline } from "./intelligence-timeline";
import { RisksPanel } from "./risks-panel";
import { CommunicationBrief } from "./communication-brief";
import { useWorkspaceSummary } from "@/lib/hooks/use-workspace-summary";
import { useWorkspaceTimeline } from "@/lib/hooks/use-workspace-timeline";
import { useWorkspaceLatestByKind } from "@/lib/hooks/use-workspace-latest";
import { useActionItems } from "@/lib/hooks/use-action-items";
import { useSubmitProjectStatus } from "@/lib/hooks/use-submit-project-status";
import { useSubmitRiskReview } from "@/lib/hooks/use-submit-risk-review";
import { useSubmitMeetingIntelligence } from "@/lib/hooks/use-submit-meeting-intelligence";

vi.mock("@/lib/hooks/use-workspace-summary", () => ({ useWorkspaceSummary: vi.fn() }));
vi.mock("@/lib/hooks/use-workspace-timeline", () => ({ useWorkspaceTimeline: vi.fn() }));
vi.mock("@/lib/hooks/use-workspace-latest", () => ({ useWorkspaceLatestByKind: vi.fn() }));
// The 3 Executive Briefs each mount ActionsContextLine (TIP-008 Incremento
// 3), which calls this hook -- mocked here for the same reason as the
// query hooks above: this file exercises the panels in isolation.
vi.mock("@/lib/hooks/use-action-items", () => ({ useActionItems: vi.fn() }));
// WorkspaceHeader mounts AnalyzeProjectDialog (TIP-005/TIP-006), which calls
// these mutation hooks -- mocked here for the same reason as the 3 query
// hooks above: this file exercises the panels in isolation, not the real
// network.
vi.mock("@/lib/hooks/use-submit-project-status", () => ({ useSubmitProjectStatus: vi.fn() }));
vi.mock("@/lib/hooks/use-submit-risk-review", () => ({ useSubmitRiskReview: vi.fn() }));
vi.mock("@/lib/hooks/use-submit-meeting-intelligence", () => ({ useSubmitMeetingIntelligence: vi.fn() }));

const mockedSummary = vi.mocked(useWorkspaceSummary);
const mockedTimeline = vi.mocked(useWorkspaceTimeline);
const mockedLatest = vi.mocked(useWorkspaceLatestByKind);
const mockedActionItems = vi.mocked(useActionItems);
const mockedSubmitStatus = vi.mocked(useSubmitProjectStatus);
const mockedSubmitRisk = vi.mocked(useSubmitRiskReview);
const mockedSubmitMeeting = vi.mocked(useSubmitMeetingIntelligence);
mockedSubmitStatus.mockReturnValue({
  mutate: vi.fn(),
  reset: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
} as never);
mockedSubmitRisk.mockReturnValue({
  mutate: vi.fn(),
  reset: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
} as never);
mockedSubmitMeeting.mockReturnValue({
  mutate: vi.fn(),
  reset: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
} as never);
// Default: no action-items data yet -- ActionsContextLine renders null,
// keeping every pre-existing test in this file unaffected. Tests that
// exercise the context line itself override this per-case.
mockedActionItems.mockReturnValue({ isPending: true, isError: false, data: undefined } as never);

const PENDING = { isPending: true, isError: false, data: undefined, refetch: vi.fn(), isFetching: false } as never;
const ERROR = { isPending: false, isError: true, data: undefined, refetch: vi.fn(), isFetching: false } as never;

function summaryState(overrides: Partial<Record<string, unknown>>) {
  return { isPending: false, isError: false, isFetching: false, refetch: vi.fn(), ...overrides } as never;
}

describe("WorkspaceHeader (Painel A, independente)", () => {
  it("shows a skeleton while pending", () => {
    mockedSummary.mockReturnValue(PENDING);
    const { container } = render(<WorkspaceHeader projectName="Aurora" />);
    expect(container.querySelector('[data-slot="skeleton"]')).not.toBeNull();
  });

  it("falls back to the raw project name on error, without crashing", () => {
    mockedSummary.mockReturnValue(ERROR);
    render(<WorkspaceHeader projectName="Aurora" />);
    expect(screen.getByRole("heading", { name: "Aurora" })).toBeInTheDocument();
  });

  it("renders the project name and health badge on success", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: {
          project_name: "Aurora",
          total_analyses: 3,
          open_risks: 2,
          pending_action_items: 1,
          latest_health_status: "red",
        },
      }),
    );
    render(<WorkspaceHeader projectName="Aurora" />);
    expect(screen.getByRole("heading", { name: "Aurora" })).toBeInTheDocument();
    expect(screen.getByText("Crítico")).toBeInTheDocument();
  });
});

describe("ExecutiveBrief (Painéis A + C fundidos, cada um com estado próprio -- Decision Momentum Rev. 2)", () => {
  it("renders the counts card even while the brief body is still loading", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: {
          project_name: "Aurora",
          total_analyses: 4,
          open_risks: 1,
          pending_action_items: 0,
          latest_health_status: "green",
        },
      }),
    );
    mockedLatest.mockReturnValue(PENDING);

    render(<ExecutiveBrief projectName="Aurora" />);
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("renders the brief body even while the counts card errored -- neither blocks the other", () => {
    mockedSummary.mockReturnValue(ERROR);
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 9,
          kind: "status",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "project_status",
            project_name: "Aurora",
            model_output: { structured: true, health_status: "green", key_findings: ["Achado real"], recommendations: [] },
          },
        },
      }),
    );

    render(<ExecutiveBrief projectName="Aurora" />);
    expect(screen.getByText("Achado real")).toBeInTheDocument();
    expect(screen.getByText("Não foi possível carregar as contagens.")).toBeInTheDocument();
  });

  it("never invents a finding -- shows a plain empty state when there is no status analysis yet", () => {
    mockedSummary.mockReturnValue(summaryState({ data: { project_name: "Aurora", total_analyses: 0, open_risks: 0, pending_action_items: 0, latest_health_status: null } }));
    mockedLatest.mockReturnValue(summaryState({ data: null }));

    render(<ExecutiveBrief projectName="Aurora" />);
    expect(screen.getByText("Nenhuma análise de status registrada ainda.")).toBeInTheDocument();
  });

  it("treats structured=true with a mismatched shape (real Demo Mode failure mode, TIP-006) the same as unstructured -- never crashes", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: { project_name: "Aurora", total_analyses: 1, open_risks: 0, pending_action_items: 0, latest_health_status: "green" },
      }),
    );
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 1,
          kind: "status",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          // structured: true, but shaped like a risk_review response instead
          // of project_status -- confirmed real failure mode, not hypothetical.
          payload: {
            agent: "project_status",
            project_name: "Aurora",
            model_output: { structured: true, risks: [], escalation_recommendation: null },
          },
        },
      }),
    );

    render(<ExecutiveBrief projectName="Aurora" />);
    expect(screen.getByText("Resposta da IA não estruturada nesta análise.")).toBeInTheDocument();
  });

  it.each([
    ["red", "Pontos de atenção", "Escalar ao patrocinador"],
    ["yellow", "Pontos de atenção", "Acompanhar de perto"],
    ["green", "Notas do período", "Manter o curso atual"],
  ] as const)(
    "health_status=%s drives the Contexto heading and Decisão sugerida via a fixed UI rule, never the AI",
    (healthStatus, expectedHeading, expectedDecision) => {
      mockedSummary.mockReturnValue(
        summaryState({
          data: {
            project_name: "Aurora",
            total_analyses: 1,
            open_risks: 0,
            pending_action_items: 0,
            latest_health_status: healthStatus,
          },
        }),
      );
      mockedLatest.mockReturnValue(
        summaryState({
          data: {
            id: 1,
            kind: "status",
            project_name: "Aurora",
            created_at: "2026-07-01T00:00:00Z",
            payload: {
              agent: "project_status",
              project_name: "Aurora",
              model_output: { structured: true, health_status: healthStatus, key_findings: ["Achado"], recommendations: [] },
            },
          },
        }),
      );

      render(<ExecutiveBrief projectName="Aurora" />);
      expect(screen.getByText(expectedHeading)).toBeInTheDocument();
      expect(screen.getByText(expectedDecision)).toBeInTheDocument();
    },
  );

  it("promotes the first recommendation to Próximo passo, keeps the rest under Também recomendado -- editorial convention, not AI ranking", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: { project_name: "Aurora", total_analyses: 1, open_risks: 0, pending_action_items: 0, latest_health_status: "yellow" },
      }),
    );
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 1,
          kind: "status",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "project_status",
            project_name: "Aurora",
            model_output: {
              structured: true,
              health_status: "yellow",
              key_findings: [],
              recommendations: ["Confirmar cronograma com o patrocinador", "Revisar escopo restante"],
            },
          },
        },
      }),
    );

    render(<ExecutiveBrief projectName="Aurora" />);
    expect(screen.getByText("Confirmar cronograma com o patrocinador")).toBeInTheDocument();
    expect(screen.getByText("Também recomendado")).toBeInTheDocument();
    expect(screen.getByText("Revisar escopo restante")).toBeInTheDocument();
  });

  it("falls back to an honest continuity statement when recommendations is empty -- never fabricates one", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: { project_name: "Aurora", total_analyses: 1, open_risks: 0, pending_action_items: 0, latest_health_status: "green" },
      }),
    );
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 1,
          kind: "status",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "project_status",
            project_name: "Aurora",
            model_output: { structured: true, health_status: "green", key_findings: [], recommendations: [] },
          },
        },
      }),
    );

    render(<ExecutiveBrief projectName="Aurora" />);
    expect(
      screen.getByText("Nenhuma recomendação registrada nesta análise — continue acompanhando o projeto."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Também recomendado")).not.toBeInTheDocument();
  });

  // TIP-008 Incremento 3 (FS-007 §2.7) -- linha de contexto "N ações exigem
  // atenção", presente só quando a contagem de urgência (atrasado + vence
  // em breve) é > 0, ausente quando é 0.
  it("shows the actions context line when the attention count is greater than zero", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: { project_name: "Aurora", total_analyses: 1, open_risks: 0, pending_action_items: 2, latest_health_status: "green" },
      }),
    );
    mockedLatest.mockReturnValue(summaryState({ data: null }));
    mockedActionItems.mockReturnValue({
      isPending: false,
      isError: false,
      data: [
        { project_name: "Aurora", description: "a", owner: null, due_date: "2000-01-01", source_analysis_id: 1, source_created_at: "2026-01-01T00:00:00Z" },
        { project_name: "Aurora", description: "b", owner: null, due_date: "2000-01-01", source_analysis_id: 2, source_created_at: "2026-01-01T00:00:00Z" },
      ],
    } as never);

    render(<ExecutiveBrief projectName="Aurora" />);
    expect(screen.getByText("2 ações exigem atenção")).toBeInTheDocument();
  });

  it("omits the actions context line when the attention count is zero", () => {
    mockedSummary.mockReturnValue(
      summaryState({
        data: { project_name: "Aurora", total_analyses: 1, open_risks: 0, pending_action_items: 0, latest_health_status: "green" },
      }),
    );
    mockedLatest.mockReturnValue(summaryState({ data: null }));
    mockedActionItems.mockReturnValue({ isPending: false, isError: false, data: [] } as never);

    render(<ExecutiveBrief projectName="Aurora" />);
    expect(screen.queryByText(/ações exigem atenção/)).not.toBeInTheDocument();
  });
});

describe("IntelligenceTimeline (Painel B, independente)", () => {
  it("shows an empty message, not an error, when there is simply no history yet", () => {
    mockedTimeline.mockReturnValue(summaryState({ data: [] }));
    render(<IntelligenceTimeline projectName="Aurora" />);
    expect(screen.getByText("Nenhuma análise registrada ainda.")).toBeInTheDocument();
  });

  it("lists analyses with a kind badge, most recent first as returned by the backend", () => {
    mockedTimeline.mockReturnValue(
      summaryState({
        data: [
          { id: 2, kind: "risk", project_name: "Aurora", created_at: "2026-07-02T10:00:00Z" },
          { id: 1, kind: "meeting", project_name: "Aurora", created_at: "2026-07-01T10:00:00Z" },
        ],
      }),
    );
    render(<IntelligenceTimeline projectName="Aurora" />);
    expect(screen.getByText("Risco")).toBeInTheDocument();
    expect(screen.getByText("Reunião")).toBeInTheDocument();
  });
});

describe("RisksPanel (Painel C, 'risk')", () => {
  it("renders risks, escalation recommendation, and the matrix on success", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 1,
          kind: "risk",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "risk_review",
            project_name: "Aurora",
            model_output: {
              structured: true,
              risks: [{ description: "Atraso", probability: "high", impact: "high", mitigation: "Plano B" }],
              escalation_recommendation: "Escalar ao sponsor",
            },
          },
        },
      }),
    );
    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("Atraso")).toBeInTheDocument();
    expect(screen.getByText(/Escalar ao sponsor/)).toBeInTheDocument();
  });

  it("handles an unstructured payload without crashing", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 1,
          kind: "risk",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: { agent: "risk_review", project_name: "Aurora", model_output: { structured: false, raw_output: "not json" } },
        },
      }),
    );
    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("Resposta da IA não estruturada nesta análise.")).toBeInTheDocument();
  });

  it("treats structured=true with a mismatched shape (real Demo Mode failure mode, TIP-006) the same as unstructured -- never crashes", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 1,
          kind: "risk",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          // structured: true, but shaped like a project_status response
          // instead of risk_review -- confirmed real failure mode.
          payload: {
            agent: "risk_review",
            project_name: "Aurora",
            model_output: { structured: true, health_status: "green", key_findings: [], recommendations: [] },
          },
        },
      }),
    );
    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("Resposta da IA não estruturada nesta análise.")).toBeInTheDocument();
  });

  it("promotes only high-attention risks (red zone), keeps the rest under Também identificado -- never hides real data", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 2,
          kind: "risk",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "risk_review",
            project_name: "Aurora",
            model_output: {
              structured: true,
              risks: [
                { description: "Atraso crítico", probability: "high", impact: "high", mitigation: "Escalar" },
                { description: "Custo baixo", probability: "low", impact: "low", mitigation: "Monitorar" },
              ],
              escalation_recommendation: null,
            },
          },
        },
      }),
    );
    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("Riscos que exigem atenção")).toBeInTheDocument();
    expect(screen.getByText("Atraso crítico")).toBeInTheDocument();
    expect(screen.getByText("Também identificado")).toBeInTheDocument();
    expect(screen.getByText("Custo baixo")).toBeInTheDocument();
    expect(screen.getByText("Priorizar mitigação imediata")).toBeInTheDocument();
  });

  it("shows the honest 'no critical risk' framing when nothing is in the attention zone", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 3,
          kind: "risk",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "risk_review",
            project_name: "Aurora",
            model_output: {
              structured: true,
              risks: [{ description: "Risco leve", probability: "low", impact: "medium", mitigation: "Acompanhar" }],
              escalation_recommendation: null,
            },
          },
        },
      }),
    );
    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("Sem riscos críticos no momento")).toBeInTheDocument();
    expect(screen.getByText("Manter monitoramento de rotina")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Nenhuma recomendação de escalonamento registrada nesta análise — continue monitorando os riscos identificados.",
      ),
    ).toBeInTheDocument();
  });

  it("never invents a risk -- shows a plain empty state when the analysis found none", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 4,
          kind: "risk",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "risk_review",
            project_name: "Aurora",
            model_output: { structured: true, risks: [], escalation_recommendation: null },
          },
        },
      }),
    );
    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("Nenhum risco identificado nesta análise.")).toBeInTheDocument();
  });

  // TIP-008 Incremento 3 (FS-007 §2.7) -- mesma linha de contexto do
  // Executive Brief, mesmo hook (useActionItems), presença condicionada
  // apenas à contagem de urgência, nunca ao conteúdo próprio deste painel.
  it("shows the actions context line when the attention count is greater than zero", () => {
    mockedLatest.mockReturnValue(summaryState({ data: null }));
    mockedActionItems.mockReturnValue({
      isPending: false,
      isError: false,
      data: [
        { project_name: "Aurora", description: "a", owner: null, due_date: "2000-01-01", source_analysis_id: 1, source_created_at: "2026-01-01T00:00:00Z" },
      ],
    } as never);

    render(<RisksPanel projectName="Aurora" />);
    expect(screen.getByText("1 ação exige atenção")).toBeInTheDocument();
  });

  it("omits the actions context line when the attention count is zero", () => {
    mockedLatest.mockReturnValue(summaryState({ data: null }));
    mockedActionItems.mockReturnValue({ isPending: false, isError: false, data: [] } as never);

    render(<RisksPanel projectName="Aurora" />);
    expect(screen.queryByText(/ação exige atenção|ações exigem atenção/)).not.toBeInTheDocument();
  });
});

describe("CommunicationBrief (Painel C, 'meeting' -- FS-006 Hierarquia Executiva)", () => {
  const meetingData = {
    id: 5,
    kind: "meeting" as const,
    project_name: "Aurora",
    created_at: "2026-07-01T00:00:00Z",
    payload: {
      agent: "meeting_intelligence",
      project_name: "Aurora",
      model_output: {
        structured: true as const,
        summary: "resumo",
        decisions: ["Decisão A"],
        action_items: [{ description: "Enviar proposta", owner: "Ana", due_date: "2026-08-01" }],
        issues: [],
        dependencies: ["Aprovação jurídica"],
      },
    },
  };

  it("renders all 6 real levels of the hierarchy from a single payload", () => {
    mockedLatest.mockReturnValue(summaryState({ data: meetingData }));
    render(<CommunicationBrief projectName="Aurora" />);
    expect(screen.getByText("resumo")).toBeInTheDocument();
    expect(screen.getByText("Decisão A")).toBeInTheDocument();
    expect(screen.getByText("Enviar proposta")).toBeInTheDocument();
    expect(screen.getByText(/Ana/)).toBeInTheDocument();
    expect(screen.getByText("Aprovação jurídica")).toBeInTheDocument();
    expect(screen.getByText("1 decisão(ões) · 0 ponto(s) de atenção · 1 responsabilidade(s)")).toBeInTheDocument();
  });

  it("suggests the next step from real issues/decisions counts -- never a fabricated one", () => {
    mockedLatest.mockReturnValue(summaryState({ data: meetingData }));
    render(<CommunicationBrief projectName="Aurora" />);
    expect(screen.getByText("Atualizar Status Executivo")).toBeInTheDocument();
  });

  it("falls back honestly when there are no issues and no decisions", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          ...meetingData,
          payload: {
            ...meetingData.payload,
            model_output: { ...meetingData.payload.model_output, decisions: [] },
          },
        },
      }),
    );
    render(<CommunicationBrief projectName="Aurora" />);
    expect(
      screen.getByText("Nenhum próximo passo adicional sugerido a partir desta reunião."),
    ).toBeInTheDocument();
  });

  it("treats structured=true with a mismatched shape the same as unstructured -- never crashes", () => {
    mockedLatest.mockReturnValue(
      summaryState({
        data: {
          id: 6,
          kind: "meeting",
          project_name: "Aurora",
          created_at: "2026-07-01T00:00:00Z",
          payload: {
            agent: "meeting_intelligence",
            project_name: "Aurora",
            model_output: { structured: true, health_status: "green", key_findings: [], recommendations: [] },
          },
        },
      }),
    );
    render(<CommunicationBrief projectName="Aurora" />);
    expect(screen.getByText("Resposta da IA não estruturada nesta análise.")).toBeInTheDocument();
  });

  // TIP-008 Incremento 3 (FS-007 §2.7) -- mesma linha de contexto, mesmo hook.
  it("shows the actions context line when the attention count is greater than zero", () => {
    mockedLatest.mockReturnValue(summaryState({ data: meetingData }));
    mockedActionItems.mockReturnValue({
      isPending: false,
      isError: false,
      data: [
        { project_name: "Aurora", description: "a", owner: null, due_date: "2000-01-01", source_analysis_id: 1, source_created_at: "2026-01-01T00:00:00Z" },
      ],
    } as never);

    render(<CommunicationBrief projectName="Aurora" />);
    expect(screen.getByText("1 ação exige atenção")).toBeInTheDocument();
  });

  it("omits the actions context line when the attention count is zero", () => {
    mockedLatest.mockReturnValue(summaryState({ data: meetingData }));
    mockedActionItems.mockReturnValue({ isPending: false, isError: false, data: [] } as never);

    render(<CommunicationBrief projectName="Aurora" />);
    expect(screen.queryByText(/ação exige atenção|ações exigem atenção/)).not.toBeInTheDocument();
  });
});
