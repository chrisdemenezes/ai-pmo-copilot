import "@testing-library/jest-dom/vitest";

// V1 Product & Capability Completion, Pacote C (Light/Dark Theme): jsdom
// does not implement window.matchMedia -- ThemeToggle (and anything that
// renders it, like Sidebar) calls it to resolve the system preference.
// Defaults to "no preference matches" (light); individual tests can
// override matches/addEventListener via vi.spyOn if they need to assert
// dark-mode-specific behavior.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as unknown as MediaQueryList;
}
