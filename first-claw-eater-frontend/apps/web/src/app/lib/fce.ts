export type DatasetCategory = "spot" | "sentiment";
export type DatasetSource = "demo" | "dexscreener" | "empty" | "rss";

export type DatasetOut = {
  dataset_id: string;
  category: string;
  source: string;
  start: string;
  end: string;
  status: string;
  error: string | null;
  created_at: string;
  updated_at: string;
  params?: Record<string, unknown>;
};

export type RunOut = {
  run_id: string;
  market_id: string;
  model_key: string;
  status: string;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
};

export type TimelinePoint = {
  observed_at: string;
  equity_quote: number;
  cash_quote: number;
};

export type PricePoint = {
  observed_at: string;
  price: number;
};

export type LlmDecision = {
  tick_time: string;
  market_id: string;
  targets: Record<string, string>;
  llm_call_id?: string | null;
  accepted: boolean;
  reject_reason?: string | null;
  next_check_seconds?: number | null;
  confidence?: string | null;
  key_signals?: string[];
  rationale?: string | null;
};

export type SummaryOut = {
  summary_text: string | null;
};

export type LiveRunOut = {
  run: RunOut | null;
};

export type PromptTemplateOut = {
  template_id: string;
  name: string;
  engine: string;
  system_template: string;
  user_template: string;
  vars_schema: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export async function apiJson<T>(
  path: string,
  init?: Omit<RequestInit, "body"> & { body?: unknown },
): Promise<T> {
  const res = await fetch(`/api/fce${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      "content-type": "application/json",
    },
    body: init?.body === undefined ? undefined : JSON.stringify(init.body),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export function isoFromLocalInput(v: string) {
  // input[type=datetime-local] returns local time without timezone.
  return new Date(v).toISOString();
}
