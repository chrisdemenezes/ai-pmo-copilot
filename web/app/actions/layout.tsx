import { AppShell } from "@/components/shell/app-shell";

export default function ActionsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
