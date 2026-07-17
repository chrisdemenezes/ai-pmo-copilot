import { AppShell } from "@/components/shell/app-shell";

export default function AprendizadosLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
