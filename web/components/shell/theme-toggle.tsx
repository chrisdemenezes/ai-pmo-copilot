"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

import { applyTheme, readStoredTheme, storeTheme, type Theme } from "@/lib/theme";

// Dispatched right after this tab changes the theme -- localStorage's own
// "storage" event only fires in OTHER tabs/windows, never the one that
// made the change, so this is what lets useSyncExternalStore re-render
// this same tab immediately after toggle().
const THEME_CHANGE_EVENT = "stratech:theme-change";

function subscribe(callback: () => void): () => void {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", callback);
  window.addEventListener(THEME_CHANGE_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    media.removeEventListener("change", callback);
    window.removeEventListener(THEME_CHANGE_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

function getSnapshot(): Theme {
  const stored = readStoredTheme();
  if (stored !== null) return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// Server render has no localStorage/matchMedia -- "light" matches the
// :root default (light) CSS, so there is nothing to correct visually
// before useSyncExternalStore reconciles against the real client value.
function getServerSnapshot(): Theme {
  return "light";
}

/**
 * V1 Product & Capability Completion, Pacote C: alterna entre Claro e
 * Escuro, persistido (localStorage), sem introduzir um terceiro tema ou
 * trocar o design system -- os mesmos tokens já calculados em RFC-001
 * Seção 5. useSyncExternalStore (não useState+useEffect) evita tanto o
 * flash de tema errado quanto uma resolução de estado externo dentro de
 * um efeito.
 */
export function ThemeToggle() {
  const resolvedTheme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const isDark = resolvedTheme === "dark";

  function toggle() {
    const next: Theme = isDark ? "light" : "dark";
    applyTheme(next);
    storeTheme(next);
    window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? "Mudar para tema claro" : "Mudar para tema escuro"}
      title={isDark ? "Tema escuro (clique para claro)" : "Tema claro (clique para escuro)"}
      className="flex size-9 shrink-0 items-center justify-center rounded-md text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink"
    >
      {isDark ? <Sun className="size-5" aria-hidden="true" /> : <Moon className="size-5" aria-hidden="true" />}
    </button>
  );
}
