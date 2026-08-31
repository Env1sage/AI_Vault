import {
  FileArchive,
  FileCode,
  FileSpreadsheet,
  FileText,
  FileVideo,
  File as FileIcon,
  Folder,
  Image as ImageIcon,
  Presentation,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { createElement, type ReactElement } from "react";

/** Purely presentational categorization of a file's real `mime_type` — no
 * data is inferred or fabricated, this only picks which icon a known MIME
 * family gets. */
export function fileTypeIcon(mimeType: string | null): LucideIcon {
  if (!mimeType) return FileIcon;
  if (mimeType.includes("folder")) return Folder;
  if (mimeType.startsWith("image/")) return ImageIcon;
  if (mimeType.startsWith("video/")) return FileVideo;
  if (mimeType.includes("spreadsheet") || mimeType.includes("csv")) return FileSpreadsheet;
  if (mimeType.includes("presentation")) return Presentation;
  if (mimeType.includes("zip") || mimeType.includes("compressed") || mimeType.includes("archive")) {
    return FileArchive;
  }
  if (
    mimeType.includes("javascript") ||
    mimeType.includes("json") ||
    mimeType.includes("xml") ||
    mimeType.includes("code")
  ) {
    return FileCode;
  }
  if (mimeType.startsWith("text/") || mimeType.includes("document") || mimeType.includes("pdf")) {
    return FileText;
  }
  return FileIcon;
}

/** Renders the icon element directly (rather than returning a component
 * reference for callers to use as a JSX tag) so the dynamic MIME-family
 * lookup doesn't trip the "components created during render" lint rule. */
export function fileTypeIconElement(
  mimeType: string | null,
  props: { className?: string },
): ReactElement {
  return createElement(fileTypeIcon(mimeType), { ...props, "aria-hidden": true });
}

export function fileTypeLabel(mimeType: string | null): string {
  if (!mimeType) return "File";
  if (mimeType.startsWith("image/")) return "Image";
  if (mimeType.startsWith("video/")) return "Video";
  if (mimeType.includes("spreadsheet") || mimeType.includes("csv")) return "Spreadsheet";
  if (mimeType.includes("presentation")) return "Presentation";
  if (mimeType.includes("pdf")) return "PDF";
  if (mimeType.includes("document")) return "Document";
  if (mimeType.includes("zip") || mimeType.includes("archive")) return "Archive";
  return mimeType.split("/").pop()?.toUpperCase() ?? "File";
}
