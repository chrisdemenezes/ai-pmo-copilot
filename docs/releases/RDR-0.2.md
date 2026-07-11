# Release Decision Record — Release 0.2

Fecha o ciclo de governança do AI Product Engineering Framework (AI-PEF) para a Release 0.2
(FS-001 — Dashboard Executivo). Trilha de auditoria: quem aprovou, em que condições, com quais
restrições.

| Campo | Valor |
|---|---|
| Release | 0.2 (FS-001 — Dashboard Executivo) |
| Data | 2026-07-11 |
| Commit | `2358a66c6fa5ee3b100042df2117cc037d46acef` (squash merge de `claude/cleanup-orphaned-files-xtvwrj` em `main`) |
| PR | [#35](https://github.com/chrisdemenezes/ai-pmo-copilot/pull/35) |
| Resultado | Aprovada |
| Ambiente autorizado | Interno / piloto controlado da Stratech |
| Ambientes bloqueados | Produção pública, clientes externos |
| Riscos aceitos | 1 (Security Finding, Alto — força bruta em `POST /api/bff/session`, sem rate limiting) |
| Riscos mitigados | 1 (Design Consistency, Média — rótulo de status unificado em português em todos os widgets, commit `59f17aa`) |
| Condição obrigatória para próxima Release | Mitigação do Security Finding: rate limiting específico de login, limitação por IP, janela configurável, testes automatizados, documentação — antes de qualquer ambiente além de interno/piloto |
| Responsável pela decisão | Product Owner |

## Achados não-bloqueantes registrados como backlog técnico

- Rota BFF `/api/bff/dashboard` não reverifica sessão internamente (depende do matcher de `proxy.ts`)
- Resposta do backend não validada em runtime (sem Zod)
- `SESSION_SECRET` ausente gera exceção não tratada em `proxy.ts`
- `aria-live` ausente nas transições de estado
- Integração da suíte E2E ao GitHub Actions (candidata a Release 0.3)

## Gates do AI-PEF percorridos

Product Review (Product Hypothesis, ADR-010) → Architecture Review → UX Review → Feature
Specification (FS-001) → Technical Implementation Plan (TIP-001) → Product Owner Approval →
Implementação (T1–T9) → Documentação (T10) → Code Review → QA Review → Release Review → **RDR**.

## Referências

- Feature Specification: `docs/product/fs-001/FS-001-feature-specification.html` (Revisão 5)
- Technical Implementation Plan: `docs/product/fs-001/TIP-001-implementation-plan.html`
- UX Review: `docs/product/fs-001/UX-REVIEW-FS001.html`
- Evidência técnica: `docs/releases/mvp-validation.md`, Evidence Entry 015
- Decisão de risco: `docs/development/01-project-structure.md`, "Decision: Security Finding (Achado #1)"
