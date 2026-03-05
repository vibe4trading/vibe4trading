export type RunOut = {
  run_id: string;
  parent_run_id?: string | null;
  market_id: string;
  model_key: string;
  status: string;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
};

export type MeOut = {
  user_id: string;
  email: string | null;
  display_name: string | null;
  api_token: string | null;
  is_admin: boolean;
  quota: {
    runs_used: number;
    runs_limit: number;
    has_quota: boolean;
  };
};

export type ModelPublicOut = {
  model_key: string;
  label: string | null;
};

export type ModelAdminOut = {
  model_key: string;
  label: string | null;
  api_base_url: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type ModelAdminCreateRequest = {
  model_key: string;
  label?: string | null;
  api_base_url?: string | null;
  enabled?: boolean;
};

export type ModelAdminUpdateRequest = {
  label?: string | null;
  api_base_url?: string | null;
  enabled?: boolean | null;
};

export type RunConfigSnapshot = {
  mode: "replay" | "live";
  run_kind?: string;
  visibility?: string;

  market_id: string;

  scheduler?: {
    base_interval_seconds?: number;
    price_tick_seconds?: number;
    min_interval_seconds?: number;
  };

  replay?: {
    pace_seconds_per_base_tick?: number;
  };
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

export type ScenarioWindowOut = {
  index: number;
  label: string;
  start: string;
  end: string;
};

export type ScenarioSetOut = {
  key: string;
  name: string;
  description: string;
  windows: ScenarioWindowOut[];

  base_interval_seconds: number;
  min_interval_seconds: number;
  price_tick_seconds: number;
  lookback_bars: number;
  timeframe: string;
  time_offset_seconds: number;
  fee_bps: number;
  initial_equity_quote: number;
};

export type ArenaSubmissionOut = {
  submission_id: string;
  scenario_set_key: string;
  market_id: string;
  model_key: string;
  prompt_template_id: string | null;
  visibility: string;
  status: string;

  windows_total: number;
  windows_completed: number;

  total_return_pct: number | null;
  avg_return_pct: number | null;

  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  ended_at: string | null;
};

export type ArenaScenarioRunOut = {
  submission_id: string;
  scenario_index: number;
  run_id: string;
  window_start: string;
  window_end: string;
  status: string;
  return_pct: number | null;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
};

export type ArenaSubmissionDetailOut = ArenaSubmissionOut & {
  runs: ArenaScenarioRunOut[];
};

export type LeaderboardEntryOut = {
  submission_id: string;
  scenario_set_key: string;
  market_id: string;
  model_key: string;
  total_return_pct: number;
  avg_return_pct: number;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  win_rate_pct: number | null;
  profit_factor: number | null;
  num_trades: number | null;
  per_window_returns: number[] | null;
  created_at: string;
};

export async function apiJson<T>(
  path: string,
  init?: Omit<RequestInit, "body"> & { body?: unknown },
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);

  try {
    const res = await fetch(`/api/v4t${path}`, {
      ...init,
      signal: init?.signal ?? controller.signal,
      headers: {
        ...(init?.headers ?? {}),
        ...(init?.body !== undefined ? { "content-type": "application/json" } : {}),
      },
      body: init?.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || `HTTP ${res.status}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export function isoFromLocalInput(v: string) {
  // input[type=datetime-local] returns local time without timezone.
  return new Date(v).toISOString();
}
