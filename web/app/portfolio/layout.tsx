import { AppShell } from "@/components/shell/app-shell";

export default function PortfolioLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
