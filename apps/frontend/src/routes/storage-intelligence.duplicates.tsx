import { Outlet, createFileRoute } from "@tanstack/react-router";

/** Thin pathless-parent shell — same reasoning as `storage-intelligence.tsx`,
 * one level down: mounts `storage-intelligence.duplicates.index.tsx` (the
 * group list) and `storage-intelligence.duplicates.$groupId.tsx` (a single
 * group's detail), each a complete `<AppShell>` page on its own. */
export const Route = createFileRoute("/storage-intelligence/duplicates")({
  component: () => <Outlet />,
});
