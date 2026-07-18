import { AppShell } from "@/components/shell/app-shell";

export default function ProgramManagementLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
