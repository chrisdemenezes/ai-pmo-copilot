import { AppShell } from "@/components/shell/app-shell";

export default function AdministracaoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
