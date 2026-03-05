"use client";

import Link from "next/link";
import * as React from "react";
import { apiJson, ArenaSubmissionOut } from "@/app/lib/v4t";

function fmt(dt: string) {
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

export default function ArenaPage() {
  const [subs, setSubs] = React.useState<ArenaSubmissionOut[]>([]);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);

  React.useEffect(() => {
    apiJson<ArenaSubmissionOut[]>("/arena/submissions")
      .then((res) => setSubs(res))
      .catch((e) => setRefreshError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <main className="trials-page-main animate-rise">
      <section className="trials-head block">
        <h1>TRIALS / Recent Runs</h1>
        <p>Click any record to view its Report.</p>
        {refreshError && <p className="text-red-600 mt-2">{refreshError}</p>}
      </section>

      <section className="trials-list block">
        {subs.length === 0 && !refreshError && (
          <div className="p-4 text-center text-[#555]">No recent runs found.</div>
        )}
        {subs.map((row) => (
          <Link
            key={row.submission_id}
            href={`/runs/${row.submission_id}`}
            className="trial-row"
          >
            <div className="trial-meta">
              <strong>{row.submission_id.slice(0, 6)}</strong>
              <span>{fmt(row.created_at)}</span>
            </div>
            <div className="trial-main">
              <p className="trial-prompt">Scenario: {row.scenario_set_key}</p>
              <div className="trial-tags">
                <span>Model: {row.model_key}</span>
                <span>Pair: {row.market_id}</span>
                {row.status && <span>Status: {row.status}</span>}
              </div>
            </div>
          </Link>
        ))}
      </section>
    </main>
  );
}
