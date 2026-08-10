import { Link, createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/unauthorized")({
  component: UnauthorizedPage,
});

function UnauthorizedPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-8 text-center">
      <h1 className="text-xl font-semibold">You don't have access to this page</h1>
      <p className="text-sm text-neutral-500">
        Your role doesn't permit this action. Contact an owner or admin if you think this is wrong.
      </p>
      <Link to="/dashboard" className="text-sm underline">
        Back to dashboard
      </Link>
    </main>
  );
}
