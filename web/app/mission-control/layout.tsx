import { AppShell } from "@/components/shell/app-shell";

export default function MissionControlLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
