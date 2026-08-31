import { Outlet, createRootRoute } from "@tanstack/react-router";

import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent() {
  return (
    <TooltipProvider delayDuration={150}>
      <div className="min-h-screen bg-background text-foreground">
        <Outlet />
      </div>
      <Toaster />
    </TooltipProvider>
  );
}
