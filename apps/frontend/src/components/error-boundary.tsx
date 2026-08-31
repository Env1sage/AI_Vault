import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/** Catches render errors so a single broken widget can't blank the whole
 * dashboard shell — required by the Phase 1 deliverable list. */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Unhandled render error:", error, info.componentStack);
  }

  override render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-background p-6 text-center text-foreground">
          <h1 className="text-lg font-semibold">Something went wrong.</h1>
          <p className="text-sm text-muted-foreground">
            Please refresh the page. If this keeps happening, contact support.
          </p>
        </div>
      );
    }

    return this.props.children;
  }
}
