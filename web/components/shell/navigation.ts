import { ClipboardList, Folder, Gavel, LayoutDashboard } from "lucide-react";

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
  { label: "Projetos", href: "/projects", icon: Folder },
  // TIP-008 Incremento 2 -- entra aqui só agora que a rota é real, com dado
  // real, estados completos e testes (regra de entrada da navegação).
  { label: "Ações", href: "/actions", icon: ClipboardList },
  // TIP-009 Incremento 3 -- mesma regra de entrada, agora para a Executive
  // Decision Queue.
  { label: "Decisões", href: "/decisions", icon: Gavel },
];
