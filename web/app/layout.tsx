import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "STRATECH",
  description:
    "Plataforma Enterprise de Gestão Estratégica de Projetos, Portfólio, PMO e Governança.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-bg text-ink font-body">
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
