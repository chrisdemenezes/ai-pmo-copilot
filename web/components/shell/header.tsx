/**
 * Pure structural wrapper -- owns no state (FS-002 Revisão 3, IRR
 * precision fix). The page supplies its own title and actions as children;
 * this component only provides the shared frame.
 */
export function Header({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center justify-between gap-4">{children}</div>;
}
