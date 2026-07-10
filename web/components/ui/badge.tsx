import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * Variants map 1:1 to backend semantics -- health_status is exactly
 * "green" | "yellow" | "red" (see docs/technical/04-api-design.md), so
 * there is no fourth color here that would correspond to nothing real.
 */
const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-mono font-semibold uppercase tracking-wide w-fit whitespace-nowrap [&_svg]:size-3",
  {
    variants: {
      variant: {
        neutral:
          "border-transparent bg-status-neutral-soft text-status-neutral",
        ok: "border-transparent bg-ok-soft text-ok",
        warn: "border-transparent bg-warn-soft text-warn",
        danger: "border-transparent bg-danger-soft text-danger",
        outline: "border-border-strong text-ink-muted",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

export interface BadgeProps
  extends React.ComponentProps<"span">,
    VariantProps<typeof badgeVariants> {
  asChild?: boolean;
}

function Badge({ className, variant, asChild = false, ...props }: BadgeProps) {
  const Comp = asChild ? Slot : "span";
  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}

/** health_status ("green" | "yellow" | "red") -> the matching Badge variant. */
export function healthStatusVariant(
  status: "green" | "yellow" | "red" | null | undefined,
): BadgeProps["variant"] {
  if (status === "green") return "ok";
  if (status === "yellow") return "warn";
  if (status === "red") return "danger";
  return "neutral";
}

export { Badge, badgeVariants };
