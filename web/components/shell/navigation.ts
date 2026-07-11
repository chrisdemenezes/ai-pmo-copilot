import { LayoutDashboard } from "lucide-react";

import type { NavItem } from "./types";

/**
 * FS-002 -- exactly one entry: the only route that exists today. Adding the
 * next real item is a line here, not a refactor of Sidebar. No disabled or
 * hidden entries for future screens -- see FS-002 Revisão 2/3 for why.
 */
export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
];
