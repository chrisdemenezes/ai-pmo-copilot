import { ClipboardList, Folder, Gavel, LayoutDashboard, Lightbulb, ListOrdered, Network, Radar, Rocket } from "lucide-react";

import type { NavItem } from "./types";

/**
 * Runtime Navigation (Platform Navigation Architecture) -- contains only
 * modules that are fully real (route, data, states, tests, Baseline
 * Visual). Adding a real item is a line here, not a refactor of Sidebar.
 * No disabled/hidden/placeholder entries -- a module is only added here
 * inside the Feature that ships it (FS-002 Revisão 2/3, reaffirmed by the
 * Platform Navigation Architecture).
 */
export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  // TIP-010 Incremento 3 -- logo após o Dashboard: Executive Navigation
  // (Onde devo olhar? -> Portfolio Intelligence) coloca esta Capability
  // como o primeiro ritual do dia, antes de Projetos/Ações/Decisões.
  { label: "Priorização", href: "/portfolio", icon: ListOrdered },
  { label: "Projetos", href: "/projects", icon: Folder },
  // Capability 02 (Release 0.2) -- Program já é entidade real, entra na
  // navegação com a mesma regra de entrada (rota real, dado real, testes).
  { label: "Program Management", href: "/program-management", icon: Network },
  // Capability 03 (Release 0.2) -- Project (Project Delivery) já é
  // entidade real, mesma regra de entrada da navegação.
  { label: "Project Delivery", href: "/project-delivery", icon: Rocket },
  // TIP-008 Incremento 2 -- entra aqui só agora que a rota é real, com dado
  // real, estados completos e testes (regra de entrada da navegação).
  { label: "Ações", href: "/actions", icon: ClipboardList },
  // TIP-009 Incremento 3 -- mesma regra de entrada, agora para a Executive
  // Decision Queue.
  { label: "Decisões", href: "/decisions", icon: Gavel },
  // TIP-012 -- último item por desenho: Organizational Intelligence é
  // consultada esporadicamente (Architecture Review §1, pergunta 4),
  // diferente do ritual diário das Capabilities anteriores.
  { label: "Aprendizados", href: "/aprendizados", icon: Lightbulb },
  // Mission Control (Sprint 1, Diretriz Complementar) -- painel do Founder.
  // Acesso hoje é apenas "autenticado" (proxy.ts), não "Founder" de fato --
  // RBAC funcional (Épico 3) ainda não existe. Limitação documentada, não
  // ocultada.
  { label: "Mission Control", href: "/mission-control", icon: Radar },
];
