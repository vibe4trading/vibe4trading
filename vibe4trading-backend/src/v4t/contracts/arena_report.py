from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ArenaSubmissionReportKeyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_return_pct: float | None = None
    avg_window_return_pct: float | None = None
    win_rate_pct: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown_pct: float | None = None
    profit_factor: float | None = None
    num_trades: int = 0
    decision_count: int = 0
    acceptance_rate_pct: float | None = None
    avg_confidence: float | None = None
    avg_target_exposure_pct: float | None = None
    window_return_dispersion_pct: float | None = None


class ArenaSubmissionReportWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_index: int
    window_code: str
    label: str
    market_id: str
    status: str
    return_pct: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown_pct: float | None = None
    win_rate_pct: float | None = None
    profit_factor: float | None = None
    num_trades: int = 0
    decision_count: int = 0
    acceptance_rate_pct: float | None = None
    avg_confidence: float | None = None
    avg_target_exposure_pct: float | None = None


class ArenaSubmissionReportWindowHighlight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_code: str
    label: str
    return_pct: float | None = None
    reason: str | None = None


class ArenaSubmissionReportNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archetype: str
    overview: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    best_window_reason: str | None = None
    worst_window_reason: str | None = None


class ArenaSubmissionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    generation_mode: Literal["llm", "fallback"] = "fallback"
    overall_score: int = Field(ge=0, le=100)
    archetype: str
    overview: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    key_metrics: ArenaSubmissionReportKeyMetrics
    best_window: ArenaSubmissionReportWindowHighlight | None = None
    worst_window: ArenaSubmissionReportWindowHighlight | None = None
    windows: list[ArenaSubmissionReportWindow] = Field(default_factory=list)
