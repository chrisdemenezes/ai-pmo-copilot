import { Sidebar } from "./sidebar";

/**
 * Sidebar + content composition. pb-16 on mobile reserves space so the
 * fixed bottom nav bar never overlaps scrollable content (RFC-001 D6).
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-full flex-1">
      <Sidebar />
      <div className="flex-1 pb-16 md:pb-0">{children}</div>
    </div>
  );
}
