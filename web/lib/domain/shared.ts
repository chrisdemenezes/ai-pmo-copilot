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

/**
 * AR-1 finding: consolidatePortfolios() (program.ts) and
 * consolidatePrograms() (project.ts) implemented the exact same
 * algorithm twice -- filter children by parent, average their progress,
 * roll up worst-case health -- differing only in field names and how
 * the parent gets rebuilt (Portfolio is a plain object spread; Program
 * goes through Program.create()). Extracted here so the rule exists
 * once; `rebuild` is the only part that legitimately differs per entity.
 */
export function consolidateFromChildren<Parent, Child>(
  parents: Parent[],
  children: Child[],
  belongsTo: (child: Child, parent: Parent) => boolean,
  childProgress: (child: Child) => number,
  childHealth: (child: Child) => DomainHealth,
  rebuild: (parent: Parent, count: number, progressPercentage: number, health: DomainHealth) => Parent,
): Parent[] {
  return parents.map((parent) => {
    const ownChildren = children.filter((child) => belongsTo(child, parent));
    if (ownChildren.length === 0) {
      return parent;
    }
    const progressPercentage = Math.round(
      ownChildren.reduce((sum, child) => sum + childProgress(child), 0) / ownChildren.length,
    );
    const health = worstHealth(ownChildren.map(childHealth));
    return rebuild(parent, ownChildren.length, progressPercentage, health);
  });
}
