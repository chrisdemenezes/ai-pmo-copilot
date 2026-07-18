/**
 * STRATECH V2 — shared domain vocabulary (Release 0.2).
 *
 * Reused across Portfolio, Program and future entities in the
 * Portfolio -> Program -> Project chain so health/status/priority mean
 * the same thing at every level of the hierarchy (CLAUDE.md: nunca
 * duplicar código — these were declared separately in Portfolio and
 * Program until Capability 02, now consolidated here).
 */

export type DomainHealth = "green" | "yellow" | "red";
export type DomainStatus = "Planejado" | "Ativo" | "Encerrado";
export type DomainPriority = "Alta" | "Média" | "Baixa";

/**
 * Worst-case rollup shared by every aggregate in the hierarchy
 * (Portfolio consolidating Programs, later Program consolidating
 * Projects): red beats yellow beats green.
 */
export function worstHealth(healths: DomainHealth[]): DomainHealth {
  if (healths.some((health) => health === "red")) return "red";
  if (healths.some((health) => health === "yellow")) return "yellow";
  return "green";
}
