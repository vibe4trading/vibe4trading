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

export type RunIndexOut = {
  items: RunOut[];
  limit: number;
  next_cursor: string | null;
  has_more: boolean;
};

export type MeOut = {
  user_id: string;
  email: string | null;
  display_name: string | null;
  has_api_token: boolean;
  is_admin: boolean;
  model_allowlist_override?: string | null;
  quota: {
    runs_used: number;
    runs_limit: number;
    has_quota: boolean;
  };
};

export type MeApiTokenOut = {
  api_token: string;
  created: boolean;
};

export type ModelPublicOut = {
  model_key: string;
  label: string | null;
  enabled: boolean;
  allowed: boolean;
  selectable: boolean;
  disabled_reason: string | null;
};

export type ModelAdminOut = {
  model_key: string;
  label: string | null;
  api_base_url: string | null;
  has_api_key: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type ModelAdminCreateRequest = {
  model_key: string;
  label?: string | null;
  api_base_url?: string | null;
  api_key?: string | null;
  enabled?: boolean;
};

export type ModelAdminUpdateRequest = {
  label?: string | null;
  api_base_url?: string | null;
  api_key?: string | null;
  clear_api_key?: boolean;
  enabled?: boolean | null;
};

export type AdminModelAccessUserOut = {
  user_id: string;
  email: string | null;
  display_name: string | null;
  model_allowlist_override: string | null;
  allowed_model_keys: string[];
  selectable_model_keys: string[];
};

export type AdminModelAccessIndexOut = {
  default_allowlist_model_keys: string[];
  default_allows_all_models: boolean;
  total_users: number;
  limit: number;
  offset: number;
  has_more: boolean;
  users: AdminModelAccessUserOut[];
};

export type AdminModelAccessUpdateRequest = {
  model_allowlist_override?: string | null;
};

export type RunConfigSnapshot = {
  mode: "replay" | "live";
  run_kind?: string;
  visibility?: string;

  market_id: string;
  model?: {
    key?: string;
    label?: string | null;
  };
  datasets?: {
    market_dataset_id?: string | null;
    sentiment_dataset_id?: string | null;
  };

  scheduler?: {
    base_interval_seconds?: number;
    price_tick_seconds?: number;
    min_interval_seconds?: number;
  };

  replay?: {
    pace_seconds_per_base_tick?: number;
  };

  prompt?: {
    prompt_text?: string;
    lookback_bars?: number;
    timeframe?: string;
    include?: string[];
  };

  execution?: {
    fee_bps?: number;
    gross_leverage_cap?: number;
    net_exposure_cap?: number;
    initial_equity_quote?: number;
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
  visibility: string;
  status: string;

  windows_total: number;
  windows_completed: number;

  total_return_pct: number | null;
  avg_return_pct: number | null;
  report_json: ArenaSubmissionReport | null;

  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  ended_at: string | null;
};

export type ArenaSubmissionIndexOut = {
  items: ArenaSubmissionOut[];
  limit: number;
  next_cursor: string | null;
  has_more: boolean;
};

export type ArenaScenarioRunOut = {
  submission_id: string;
  scenario_index: number;
  run_id: string;
  market_id: string;
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

export type ArenaSubmissionReportKeyMetrics = {
  total_return_pct: number | null;
  avg_window_return_pct: number | null;
  win_rate_pct: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  profit_factor: number | null;
  num_trades: number;
  decision_count: number;
  acceptance_rate_pct: number | null;
  avg_confidence: number | null;
  avg_target_exposure_pct: number | null;
  window_return_dispersion_pct: number | null;
};

export type ArenaSubmissionReportWindow = {
  scenario_index: number;
  window_code: string;
  label: string;
  market_id: string;
  status: string;
  return_pct: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  win_rate_pct: number | null;
  profit_factor: number | null;
  num_trades: number;
  decision_count: number;
  acceptance_rate_pct: number | null;
  avg_confidence: number | null;
  avg_target_exposure_pct: number | null;
};

export type ArenaSubmissionReportHighlight = {
  window_code: string;
  label: string;
  return_pct: number | null;
  reason: string | null;
};

export type ArenaSubmissionReport = {
  schema_version: 1;
  generation_mode: "llm" | "fallback";
  overall_score: number;
  archetype: string;
  overview: string;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  key_metrics: ArenaSubmissionReportKeyMetrics;
  best_window: ArenaSubmissionReportHighlight | null;
  worst_window: ArenaSubmissionReportHighlight | null;
  windows: ArenaSubmissionReportWindow[];
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
