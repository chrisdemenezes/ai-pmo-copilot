import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "./providers";
import { NO_FLASH_THEME_SCRIPT } from "@/lib/theme";
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
      <head>
        {/* V1 Product & Capability Completion, Pacote C: aplica a escolha
            manual de tema antes da primeira pintura -- sem isso, a página
            renderizaria com o tema do sistema por um instante e só depois
            trocaria para a escolha salva, gerando um flash perceptível. */}
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH_THEME_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col bg-bg text-ink font-body">
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
