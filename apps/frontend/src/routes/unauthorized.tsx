import { Link, createFileRoute } from "@tanstack/react-router";
import { ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/unauthorized")({
  component: UnauthorizedPage,
});

function UnauthorizedPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-8 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-destructive-muted text-destructive shadow-clay-sm">
        <ShieldAlert className="size-7" />
      </div>
      <div>
        <h1 className="text-lg font-semibold">You don&rsquo;t have access to this page</h1>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Your role doesn&rsquo;t permit this action. Contact an owner or admin if you think this
          is wrong.
        </p>
      </div>
      <Button asChild>
        <Link to="/dashboard">Back to dashboard</Link>
      </Button>
    </main>
  );
}
