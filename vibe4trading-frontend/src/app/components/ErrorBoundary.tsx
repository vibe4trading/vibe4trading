import * as React from "react";
import { Link } from "react-router-dom";

type ErrorBoundaryProps = {
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
  error: Error | null;
};

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center px-6 py-24 text-center">
          <h1 className="text-5xl font-bold tracking-tight text-white">Error</h1>
          <p className="mt-4 text-lg text-zinc-400">Something went wrong.</p>
          {this.state.error && (
            <pre className="mt-4 max-w-full overflow-auto rounded border border-zinc-700 bg-zinc-900/50 p-4 text-left text-sm text-zinc-400">
              {this.state.error.message}
            </pre>
          )}
          <div className="mt-8 flex gap-4">
            <button
              type="button"
              onClick={() => this.setState({ hasError: false, error: null })}
              className="border border-zinc-600 px-6 py-3 text-sm font-medium uppercase tracking-widest text-zinc-300 transition-colors hover:border-white hover:text-white"
            >
              Try Again
            </button>
            <Link
              to="/"
              className="border border-zinc-600 px-6 py-3 text-sm font-medium uppercase tracking-widest text-zinc-300 transition-colors hover:border-white hover:text-white"
            >
              Back to Home
            </Link>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}
