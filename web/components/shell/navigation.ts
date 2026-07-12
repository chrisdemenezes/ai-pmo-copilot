import { Folder, LayoutDashboard } from "lucide-react";

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
];
