import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="font-mono text-xs uppercase tracking-wide text-accent">
        Sprint 1 de 6
      </p>
      <h1 className="font-display text-2xl font-bold text-ink">
        AI PMO Copilot
      </h1>
      <p className="max-w-md text-ink-muted">
        O Design System foi construído neste sprint. O Dashboard de
        portfólio (Sprint 2) ainda não existe.
      </p>
      <Link
        href="/style-guide"
        className="font-medium text-accent underline underline-offset-4"
      >
        Ver Style Guide
      </Link>
    </div>
  );
}
