import { AppShell } from "@/components/shell/app-shell";

export default function ProjectDeliveryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
