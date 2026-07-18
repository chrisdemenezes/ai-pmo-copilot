"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge, healthStatusVariant } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const COLOR_TOKENS: Array<{ name: string; swatch: string }> = [
  { name: "bg", swatch: "bg-bg border border-border-strong" },
  { name: "surface", swatch: "bg-surface border border-border-strong" },
  { name: "surface-2", swatch: "bg-surface-2" },
  { name: "ink", swatch: "bg-ink" },
  { name: "ink-muted", swatch: "bg-ink-muted" },
  { name: "accent", swatch: "bg-accent" },
  { name: "accent-ink", swatch: "bg-accent-ink" },
  { name: "ok", swatch: "bg-ok" },
  { name: "warn", swatch: "bg-warn" },
  { name: "danger", swatch: "bg-danger" },
];

const HEALTH_STATUSES = ["green", "yellow", "red", null] as const;

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-border py-10 first:border-t-0 first:pt-0">
      <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
      {description ? (
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">{description}</p>
      ) : null}
      <div className="mt-6">{children}</div>
    </section>
  );
}

export default function StyleGuidePage() {
  const [charCount, setCharCount] = useState(0);

  return (
    <div className="mx-auto w-full max-w-4xl px-6 py-12">
      <header className="mb-12">
        <p className="font-mono text-xs uppercase tracking-wide text-accent">
          STRATECH V2 · Design System
        </p>
        <h1 className="mt-2 font-display text-3xl font-bold text-ink">
          STRATECH — Style Guide
        </h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Tokens e primitivos vivos, consolidados a partir do Design System da
          V1 (RFC-001 Seção 5) para a evolução Enterprise da V2. Nenhum dado
          de API real nesta página.
        </p>
      </header>

      <Section
        title="Cor"
        description="Accent índigo, distinto do azul/teal usado nos relatórios de engenharia internos. Status mapeados 1:1 ao contrato real do backend (health_status: green/yellow/red)."
      >
        <div className="flex flex-wrap gap-4">
          {COLOR_TOKENS.map((token) => (
            <div key={token.name} className="flex flex-col items-center gap-2">
              <div className={`size-14 rounded-md ${token.swatch}`} />
              <span className="font-mono text-xs text-ink-muted">
                {token.name}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Tipografia">
        <div className="space-y-4">
          <div>
            <p className="font-mono text-xs text-ink-faint">display</p>
            <p className="font-display text-2xl font-bold text-ink">
              Resumo de Portfólio
            </p>
          </div>
          <div>
            <p className="font-mono text-xs text-ink-faint">body</p>
            <p className="text-ink">3 riscos abertos, 1 ação pendente</p>
          </div>
          <div>
            <p className="font-mono text-xs text-ink-faint">mono / dado</p>
            <p className="font-mono text-sm text-ink-muted">
              req_id: a30e7f2a-d18e-4590-b50e-87721087e127
            </p>
          </div>
        </div>
      </Section>

      <Section title="Badge — semântica de status do backend">
        <div className="flex flex-wrap gap-3">
          {HEALTH_STATUSES.map((status) => (
            <Badge key={String(status)} variant={healthStatusVariant(status)}>
              {status ?? "sem status"}
            </Badge>
          ))}
          <Badge variant="outline">outline</Badge>
        </div>
      </Section>

      <Section title="Button">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Default</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button size="sm">Small</Button>
          <Button disabled>Disabled</Button>
        </div>
      </Section>

      <Section
        title="Input, Textarea, Label"
        description="O contador de caracteres espelha exatamente a validação real do backend: min_length=10, max_length=20000 em transcript/project_context (src/api/routes/intelligence.py)."
      >
        <div className="max-w-md space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="project_name">Nome do projeto (opcional)</Label>
            <Input id="project_name" placeholder="Multilift" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="transcript">Transcrição</Label>
            <Textarea
              id="transcript"
              placeholder="Cole a transcrição da reunião..."
              maxLength={20000}
              onChange={(event) => setCharCount(event.target.value.length)}
            />
            <p className="text-right font-mono text-xs text-ink-faint">
              {charCount}/20000{charCount > 0 && charCount < 10 ? " · mínimo 10" : ""}
            </p>
          </div>
        </div>
      </Section>

      <Section title="Select">
        <Select defaultValue="meeting">
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="meeting">Reunião</SelectItem>
            <SelectItem value="risk">Risco</SelectItem>
            <SelectItem value="status">Status</SelectItem>
          </SelectContent>
        </Select>
      </Section>

      <Section title="Tabs">
        <Tabs defaultValue="meeting" className="max-w-md">
          <TabsList>
            <TabsTrigger value="meeting">Reunião</TabsTrigger>
            <TabsTrigger value="risk">Risco</TabsTrigger>
            <TabsTrigger value="status">Status</TabsTrigger>
          </TabsList>
          <TabsContent value="meeting" className="text-sm text-ink-muted">
            POST /api/meetings/analyze
          </TabsContent>
          <TabsContent value="risk" className="text-sm text-ink-muted">
            POST /api/risks/analyze
          </TabsContent>
          <TabsContent value="status" className="text-sm text-ink-muted">
            POST /api/projects/analyze
          </TabsContent>
        </Tabs>
      </Section>

      <Section title="Dialog">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">Abrir diálogo</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirmar envio</DialogTitle>
              <DialogDescription>
                Este é o padrão de diálogo do Design System — Radix Dialog,
                sem dependência de runtime além do que já está no
                package.json.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancelar</Button>
              </DialogClose>
              <DialogClose asChild>
                <Button>Confirmar</Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Section>

      <Section title="Toast">
        <Button
          variant="outline"
          onClick={() =>
            toast("Análise salva", {
              description: "req_id: a30e7f2a-d18e-4590-b50e-87721087e127",
            })
          }
        >
          Disparar toast
        </Button>
      </Section>

      <Section title="Skeleton (estado de loading)">
        <div className="max-w-sm space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-20 w-full" />
        </div>
      </Section>

      <Section title="Card">
        <Card className="max-w-sm">
          <CardHeader>
            <CardTitle>Multilift</CardTitle>
            <CardDescription>Resumo de projeto</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-2">
            <Badge variant={healthStatusVariant("yellow")}>yellow</Badge>
            <span className="text-sm text-ink-muted">2 riscos abertos</span>
          </CardContent>
        </Card>
      </Section>

      <Section
        title="Table"
        description="Base para listagens de Portfólio, Projetos e Documentos (Sprint 1)."
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Projeto</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Progresso</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Multilift</TableCell>
              <TableCell>
                <Badge variant={healthStatusVariant("yellow")}>yellow</Badge>
              </TableCell>
              <TableCell className="w-40">
                <Progress value={62} />
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Aurora</TableCell>
              <TableCell>
                <Badge variant={healthStatusVariant("green")}>green</Badge>
              </TableCell>
              <TableCell className="w-40">
                <Progress value={91} />
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Section>

      <Section title="Tooltip">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline">Passe o mouse</Button>
          </TooltipTrigger>
          <TooltipContent>KPI: % de conclusão do cronograma</TooltipContent>
        </Tooltip>
      </Section>

      <Section title="Avatar">
        <div className="flex gap-3">
          <Avatar>
            <AvatarFallback>AN</AvatarFallback>
          </Avatar>
          <Avatar>
            <AvatarFallback>CP</AvatarFallback>
          </Avatar>
        </div>
      </Section>
    </div>
  );
}
