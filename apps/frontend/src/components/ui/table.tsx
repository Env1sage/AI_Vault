import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Styled to match MarkdownMessage's own GFM table rendering so a table
 * inside an AI response reads consistently whether it came from prose
 * markdown or a structured renderer. */
export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className={cn("w-full border-collapse text-xs", className)} {...props} />
    </div>
  );
}

export function TableHeader({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("bg-secondary", className)} {...props} />;
}

export function TableBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={className} {...props} />;
}

export function TableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr className={cn("transition-colors hover:bg-secondary/60", className)} {...props} />
  );
}

export function TableHead({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("border-b border-border px-2.5 py-1.5 text-left font-medium", className)}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("border-b border-border/60 px-2.5 py-1.5 align-top", className)} {...props} />
  );
}
