from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from v4t.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class EventRow(Base):
    __tablename__ = "events"

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(256), nullable=False)

    dataset_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    run_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)

    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    __table_args__ = (
        UniqueConstraint("dataset_id", "event_type", "dedupe_key", name="uq_events_dataset_dedupe"),
        UniqueConstraint("run_id", "event_type", "dedupe_key", name="uq_events_run_dedupe"),
    )


class UserRow(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    oidc_issuer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    oidc_sub: Mapped[str | None] = mapped_column(String(256), nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(
        String(42), nullable=True, unique=True, index=True
    )
    api_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    model_allowlist_override: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    oidc_groups: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (UniqueConstraint("oidc_issuer", "oidc_sub", name="uq_users_oidc"),)


class LlmModelRow(Base):
    __tablename__ = "llm_models"

    model_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    api_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class UserQuotaRow(Base):
    __tablename__ = "user_quotas"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    quota_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    runs_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runs_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=3)


class DatasetRow(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class PromptTemplateRow(Base):
    __tablename__ = "prompt_templates"

    template_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    engine: Mapped[str] = mapped_column(String(32), nullable=False, default="mustache")
    system_template: Mapped[str] = mapped_column(Text, nullable=False)
    user_template: Mapped[str] = mapped_column(Text, nullable=False)
    vars_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class RunConfigSnapshotRow(Base):
    __tablename__ = "run_config_snapshots"

    config_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class RunRow(Base):
    __tablename__ = "runs"

    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    parent_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("runs.run_id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="single_window")
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="private")
    market_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    config_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("run_config_snapshots.config_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    summary_call_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class RunDatasetRow(Base):
    __tablename__ = "run_datasets"

    run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("datasets.dataset_id", ondelete="CASCADE"), nullable=False, index=True
    )


class LlmCallRow(Base):
    __tablename__ = "llm_calls"

    call_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("runs.run_id", ondelete="SET NULL"), nullable=True, index=True
    )
    dataset_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("datasets.dataset_id", ondelete="SET NULL"), nullable=True, index=True
    )
    submission_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("arena_submissions.submission_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    prompt: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    response_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_parsed: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class JobRow(Base):
    __tablename__ = "jobs"

    job_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    dataset_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (UniqueConstraint("job_type", "run_id", name="uq_jobs_type_run"),)


class PortfolioSnapshotRow(Base):
    __tablename__ = "portfolio_snapshots"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    equity_quote: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    cash_quote: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    positions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("run_id", "observed_at", name="uq_portfolio_snapshots_run_time"),
    )


class ArenaSubmissionRow(Base):
    __tablename__ = "arena_submissions"

    submission_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )

    scenario_set_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_template_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    prompt_vars: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="public")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    windows_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    windows_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    total_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    avg_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    report_call_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    report_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ArenaSubmissionRunRow(Base):
    __tablename__ = "arena_submission_runs"

    submission_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("arena_submissions.submission_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    scenario_index: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    return_pct: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (UniqueConstraint("run_id", name="uq_arena_submission_runs_run_id"),)
