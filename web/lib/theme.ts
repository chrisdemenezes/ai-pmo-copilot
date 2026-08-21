/**
 * V1 Product & Capability Completion, Pacote C: persistência da escolha
 * manual de tema (RFC-001 Seção 5 -- data-theme="dark"/"light" sobre
 * @media (prefers-color-scheme: dark)). "Sistema" (nenhuma escolha
 * explícita) é o padrão -- remover a chave equivale a seguir o SO de novo.
 */
export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "stratech-theme";

export function readStoredTheme(): Theme | null {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    // Private browsing / storage blocked -- falls back to "Sistema".
    return null;
  }
}

export function applyTheme(theme: Theme | null): void {
  if (theme === null) {
    document.documentElement.removeAttribute("data-theme");
    return;
  }
  document.documentElement.setAttribute("data-theme", theme);
}

export function storeTheme(theme: Theme | null): void {
  try {
    if (theme === null) {
      window.localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    }
  } catch {
    // Private browsing / storage blocked -- theme still applies for this
    // page load via applyTheme(), just doesn't persist across reloads.
  }
}

/**
 * Script síncrono embutido no <head> (evita flash de tema errado antes da
 * hidratação do React) -- lê a mesma chave de localStorage e aplica
 * data-theme no <html> antes da primeira pintura.
 */
export const NO_FLASH_THEME_SCRIPT = `
(function () {
  try {
    var t = window.localStorage.getItem("${THEME_STORAGE_KEY}");
    if (t === "light" || t === "dark") {
      document.documentElement.setAttribute("data-theme", t);
    }
  } catch (e) {}
})();
`;
