import { redirect } from "next/navigation";

/**
 * FS-002 -- the stale "Sprint 1 de 6" placeholder claimed the Dashboard
 * didn't exist, which stopped being true at Release 0.2. Redirects into the
 * one real authenticated route; the existing proxy.ts gate (unchanged)
 * sends unauthenticated visitors on to /entrar from there.
 */
export default function Home() {
  redirect("/dashboard");
}
