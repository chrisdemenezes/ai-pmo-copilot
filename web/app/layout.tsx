import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI PMO Copilot",
  description:
    "Assistente de IA para governança de projetos, análise de reuniões, riscos e status.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-bg text-ink font-body">
        {children}
        <Toaster />
      </body>
    </html>
  );
}
