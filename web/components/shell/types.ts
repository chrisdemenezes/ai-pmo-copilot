import type { LucideIcon } from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /**
   * V1 Product & Capability Completion, Pacote B: rótulo de agrupamento
   * visual opcional -- itens consecutivos com o mesmo `group` ganham um
   * cabeçalho de seção no Sidebar (Projetos/Program Management/Project
   * Delivery/Priorização pertencem à mesma cadeia de execução). Não afeta
   * roteamento, RBAC ou a ordem da lista -- puramente apresentacional.
   */
  group?: string;
}
