"""init

Revision ID: 0001_init
Revises:
Create Date: 2026-03-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("event_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=256), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "dataset_id", "event_type", "dedupe_key", name="uq_events_dataset_dedupe"
        ),
        sa.UniqueConstraint("run_id", "event_type", "dedupe_key", name="uq_events_run_dedupe"),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"], unique=False)
    op.create_index("ix_events_observed_at", "events", ["observed_at"], unique=False)
    op.create_index("ix_events_dataset_id", "events", ["dataset_id"], unique=False)
    op.create_index("ix_events_run_id", "events", ["run_id"], unique=False)

    op.create_table(
        "users",
        sa.Column("user_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "datasets",
        sa.Column("dataset_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_datasets_category", "datasets", ["category"], unique=False)
    op.create_index("ix_datasets_status", "datasets", ["status"], unique=False)

    op.create_table(
        "prompt_templates",
        sa.Column("template_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("engine", sa.String(length=32), nullable=False),
        sa.Column("system_template", sa.Text(), nullable=False),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column("vars_schema", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_prompt_templates_owner_user_id",
        "prompt_templates",
        ["owner_user_id"],
        unique=False,
    )

    op.create_table(
        "run_config_snapshots",
        sa.Column("config_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "runs",
        sa.Column("run_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("market_id", sa.String(length=256), nullable=False),
        sa.Column("model_key", sa.String(length=128), nullable=False),
        sa.Column("config_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stop_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_call_id", sa.Uuid(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_runs_status", "runs", ["status"], unique=False)
    op.create_index("ix_runs_market_id", "runs", ["market_id"], unique=False)
    op.create_index("ix_runs_owner_user_id", "runs", ["owner_user_id"], unique=False)
    op.create_index("ix_runs_config_id", "runs", ["config_id"], unique=False)

    op.create_table(
        "run_datasets",
        sa.Column("run_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("category", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
    )
    op.create_index("ix_run_datasets_dataset_id", "run_datasets", ["dataset_id"], unique=False)

    op.create_table(
        "llm_calls",
        sa.Column("call_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=True),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prompt", sa.JSON(), nullable=False),
        sa.Column("response_raw", sa.Text(), nullable=True),
        sa.Column("response_parsed", sa.JSON(), nullable=True),
        sa.Column("usage", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_calls_run_id", "llm_calls", ["run_id"], unique=False)
    op.create_index("ix_llm_calls_dataset_id", "llm_calls", ["dataset_id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("job_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"], unique=False)
    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("ix_jobs_run_id", "jobs", ["run_id"], unique=False)
    op.create_index("ix_jobs_dataset_id", "jobs", ["dataset_id"], unique=False)

    op.create_table(
        "portfolio_snapshots",
        sa.Column("snapshot_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity_quote", sa.Numeric(38, 18), nullable=False),
        sa.Column("cash_quote", sa.Numeric(38, 18), nullable=False),
        sa.Column("positions", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "observed_at", name="uq_portfolio_snapshots_run_time"),
    )
    op.create_index(
        "ix_portfolio_snapshots_run_id",
        "portfolio_snapshots",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_portfolio_snapshots_observed_at",
        "portfolio_snapshots",
        ["observed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_snapshots_observed_at", table_name="portfolio_snapshots")
    op.drop_index("ix_portfolio_snapshots_run_id", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")

    op.drop_index("ix_jobs_dataset_id", table_name="jobs")
    op.drop_index("ix_jobs_run_id", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_llm_calls_dataset_id", table_name="llm_calls")
    op.drop_index("ix_llm_calls_run_id", table_name="llm_calls")
    op.drop_table("llm_calls")

    op.drop_index("ix_run_datasets_dataset_id", table_name="run_datasets")
    op.drop_table("run_datasets")

    op.drop_index("ix_runs_config_id", table_name="runs")
    op.drop_index("ix_runs_owner_user_id", table_name="runs")
    op.drop_index("ix_runs_market_id", table_name="runs")
    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_table("runs")

    op.drop_table("run_config_snapshots")

    op.drop_index("ix_prompt_templates_owner_user_id", table_name="prompt_templates")
    op.drop_table("prompt_templates")

    op.drop_index("ix_datasets_status", table_name="datasets")
    op.drop_index("ix_datasets_category", table_name="datasets")
    op.drop_table("datasets")

    op.drop_table("users")

    op.drop_index("ix_events_run_id", table_name="events")
    op.drop_index("ix_events_dataset_id", table_name="events")
    op.drop_index("ix_events_observed_at", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_table("events")
