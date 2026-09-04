import { Link } from "@tanstack/react-router";
import type { Citation } from "@vault/types";
import { ArrowRight } from "lucide-react";

import { Card } from "@/components/ui/card";
import { fileTypeIconElement, fileTypeLabel } from "@/lib/file-icon";
import { formatBytes } from "@/lib/format-bytes";

/** Expanded single-file layout for `get_file` answers — the one tool that
 * always resolves to exactly one citation, so it earns a bigger card
 * instead of a one-row list. Only shows what `citations[]` actually
 * carries (name/size/mime); everything else the tool returns (owner,
 * sharing, timestamps, AI summary) stays in the prose paragraph above,
 * since that data isn't present on the Citation type. */
export function AIFileDetailCard({ citation }: { citation: Citation }) {
  return (
    <Card className="w-full max-w-[85%] p-3">
      <Link to="/files/$fileId" params={{ fileId: citation.file_id }} className="flex items-center gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
          {fileTypeIconElement(citation.file_mime_type, { className: "size-5" })}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-foreground/90">
            {citation.file_name ?? "View file"}
          </span>
          <span className="block text-xs text-muted-foreground">
            {fileTypeLabel(citation.file_mime_type)}
            {citation.file_size_bytes !== null && ` · ${formatBytes(citation.file_size_bytes)}`}
          </span>
        </span>
        <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
      </Link>
    </Card>
  );
}
