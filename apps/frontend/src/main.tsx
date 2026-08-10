import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";

import { ErrorBoundary } from "@/components/error-boundary";
import { LoadingScreen } from "@/components/loading-screen";
import { queryClient } from "@/lib/query-client";
import { useAuthStore } from "@/stores/auth-store";

import "./index.css";
import { routeTree } from "./routeTree.gen";

const router = createRouter({ routeTree, defaultPreload: "intent" });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}
const root = createRoot(rootElement);

// Session recovery (Phase 2 deliverable): resolve whether a refresh cookie
// from a previous visit is still valid *before* the router's route guards
// (beforeLoad) run, so they see a settled "authenticated"/"unauthenticated"
// status rather than the initial "idle" one.
async function bootstrap(): Promise<void> {
  await useAuthStore.getState().initialize();

  root.render(
    <StrictMode>
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <Suspense fallback={<LoadingScreen />}>
            <RouterProvider router={router} />
          </Suspense>
        </QueryClientProvider>
      </ErrorBoundary>
    </StrictMode>,
  );
}

void bootstrap();
