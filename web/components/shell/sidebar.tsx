"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./navigation";

/**
 * Responsive behavior reuses RFC-001 Decision D6 (already-approved sidebar
 * breakpoint pattern), adapted to the single real nav item instead of the
 * 3 originally speculated there: <768px bottom bar, 768-1023px icon rail,
 * >=1024px full sidebar with labels.
 */
export function Sidebar() {
  const pathname = usePathname();

  return (
    <>
      <div
        data-testid="sidebar-nav"
        className="hidden shrink-0 flex-col border-r border-border bg-surface md:flex md:w-14 lg:w-[220px]"
      >
        <div className="flex items-center gap-3 border-b border-border p-3 md:justify-center lg:justify-start">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent text-white">
            <Sparkles className="size-4" aria-hidden="true" />
          </div>
          <span className="hidden font-display text-sm font-semibold text-ink lg:inline">
            STRATECH
          </span>
        </div>

        <nav aria-label="Navegação principal" className="flex flex-col gap-1 p-2">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent-soft text-accent-ink"
                    : "text-ink-muted hover:bg-surface-2 hover:text-ink",
                )}
              >
                <Icon className="size-5 shrink-0" aria-hidden="true" />
                <span className="hidden lg:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <nav
        data-testid="bottom-nav"
        aria-label="Navegação principal"
        className="fixed inset-x-0 bottom-0 z-10 flex border-t border-border bg-surface md:hidden"
      >
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex min-w-0 flex-1 flex-col items-center gap-1 py-2 text-xs font-medium",
                isActive ? "text-accent-ink" : "text-ink-muted",
              )}
            >
              <Icon className="size-5 shrink-0" aria-hidden="true" />
              <span className="w-full truncate text-center">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
