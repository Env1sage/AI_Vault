import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="presentation"
      aria-hidden="true"
      className={cn(
        "animate-shimmer rounded-md bg-[linear-gradient(90deg,var(--muted)_25%,var(--secondary)_37%,var(--muted)_63%)]",
        "bg-[length:400%_100%]",
        className,
      )}
      {...props}
    />
  );
}
