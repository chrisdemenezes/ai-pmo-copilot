"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./navigation";
import { ThemeToggle } from "./theme-toggle";

/**
 * Responsive behavior reuses RFC-001 Decision D6 (already-approved sidebar
 * breakpoint pattern), adapted to the single real nav item instead of the
 * 3 originally speculated there: <768px bottom bar, 768-1023px icon rail,
 * >=1024px full sidebar with labels.
 */
export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  // Same DELETE /api/bff/session + router.push/refresh pattern already used
  // by the POST at login (app/entrar/page.tsx) -- the only session mutation
  // this app has. The cookie is always expired server-side regardless of
  // the fetch outcome (web/app/api/bff/session/route.ts DELETE, best-effort
  // backend revocation), so navigation never depends on the response.
  async function handleLogout() {
    await fetch("/api/bff/session", { method: "DELETE" });
    router.push("/entrar");
    router.refresh();
  }

  return (
    <>
      <div
        data-testid="sidebar-nav"
        className="hidden shrink-0 flex-col border-r border-border bg-surface md:sticky md:top-0 md:flex md:h-screen md:w-14 md:overflow-y-auto lg:w-[220px]"
      >
        <div className="flex items-center gap-3 border-b border-border p-3 md:justify-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent text-white">
              <Sparkles className="size-4" aria-hidden="true" />
            </div>
            <span className="hidden font-display text-sm font-semibold text-ink lg:inline">
              STRATECH
            </span>
          </div>
          {/* md (ícone-rail, 56px) não tem espaço para o logo + o toggle
              lado a lado -- reaproveitado no lg (sidebar completa) e no
              bottom nav mobile (abaixo). */}
          <div className="hidden lg:block">
            <ThemeToggle />
          </div>
        </div>

        <nav aria-label="Navegação principal" className="flex flex-1 flex-col gap-1 p-2">
          {NAV_ITEMS.map((item, index) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            // Pacote B: um cabeçalho de grupo aparece só na primeira vez
            // que esse `group` surge em sequência -- nunca reordena ou
            // duplica itens, puramente apresentacional (lg apenas, mesma
            // regra do rótulo textual dos links).
            const showGroupHeader = item.group !== undefined && NAV_ITEMS[index - 1]?.group !== item.group;
            return (
              <div key={item.href} className="flex flex-col">
                {showGroupHeader && (
                  <p className="hidden px-3 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide text-ink-muted lg:block">
                    {item.group}
                  </p>
                )}
                <Link
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
              </div>
            );
          })}
        </nav>

        <div className="border-t border-border p-2">
          <button
            type="button"
            onClick={handleLogout}
            aria-label="Sair"
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <LogOut className="size-5 shrink-0" aria-hidden="true" />
            <span className="hidden lg:inline" aria-hidden="true">Sair</span>
          </button>
        </div>
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
        <button
          type="button"
          onClick={handleLogout}
          aria-label="Sair"
          className="flex min-w-0 flex-1 flex-col items-center gap-1 py-2 text-xs font-medium text-ink-muted"
        >
          <LogOut className="size-5 shrink-0" aria-hidden="true" />
          <span className="w-full truncate text-center" aria-hidden="true">Sair</span>
        </button>
        <div className="flex shrink-0 items-center justify-center px-1">
          <ThemeToggle />
        </div>
      </nav>
    </>
  );
}
