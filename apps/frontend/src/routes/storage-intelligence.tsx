import { Outlet, createFileRoute } from "@tanstack/react-router";

/** Thin pathless-parent shell — required so the router has somewhere to
 * mount `storage-intelligence.index.tsx` (the dashboard) and its sibling
 * detail pages (`.candidates`, `.large-files`, etc). Each of those already
 * renders its own complete `<AppShell>` page, so this route intentionally
 * renders nothing but the outlet. */
export const Route = createFileRoute("/storage-intelligence")({
  component: () => <Outlet />,
});
