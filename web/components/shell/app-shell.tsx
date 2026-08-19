import { Sidebar } from "./sidebar";

/**
 * Sidebar + content composition. pb-16 on mobile reserves space so the
 * fixed bottom nav bar never overlaps scrollable content (RFC-001 D6).
 *
 * min-h-screen (not min-h-full) caps the outer flex row to the viewport
 * height instead of letting it grow past it when content is tall -- that
 * growth used to drag the desktop sidebar (a flex sibling under the default
 * align-items:stretch) past the viewport too, making "Sair" reachable only
 * by scrolling the entire page (Local V1 Pilot Hardening Review, F6).
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-1">
      <Sidebar />
      <div data-testid="app-content" className="flex-1 pb-16 md:pb-0">
        {children}
      </div>
    </div>
  );
}
