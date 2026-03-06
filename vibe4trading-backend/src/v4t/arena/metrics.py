"""Compute trading performance metrics from portfolio snapshots and fill events."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.contracts.payloads import SimFillPayload
from v4t.db.models import EventRow, PortfolioSnapshotRow


@dataclass
class RunMetrics:
    sharpe_ratio: Decimal
    max_drawdown_pct: Decimal
    win_rate_pct: Decimal
    profit_factor: Decimal
    num_trades: int


def compute_run_metrics(session: Session, *, run_id: UUID) -> RunMetrics:
    """Compute performance metrics for a single run from its event log."""

    snapshots = _load_equity_series(session, run_id)
    fills = _load_fills(session, run_id)

    sharpe = _compute_sharpe(snapshots)
    max_dd = _compute_max_drawdown(snapshots)
    win_rate, profit_fac, n_trades = _compute_trade_stats(fills)

    return RunMetrics(
        sharpe_ratio=sharpe,
        max_drawdown_pct=max_dd,
        win_rate_pct=win_rate,
        profit_factor=profit_fac,
        num_trades=n_trades,
    )


def _load_equity_series(session: Session, run_id: UUID) -> list[Decimal]:
    rows = list(
        session.execute(
            select(PortfolioSnapshotRow.equity_quote)
            .where(PortfolioSnapshotRow.run_id == run_id)
            .order_by(PortfolioSnapshotRow.observed_at)
        )
        .scalars()
        .all()
    )
    return rows


def _load_fills(session: Session, run_id: UUID) -> list[SimFillPayload]:
    rows = list(
        session.execute(
            select(EventRow)
            .where(EventRow.run_id == run_id, EventRow.event_type == "sim.fill")
            .order_by(EventRow.observed_at)
        )
        .scalars()
        .all()
    )
    return [SimFillPayload.model_validate(r.payload) for r in rows]


def _compute_sharpe(equity_series: list[Decimal]) -> Decimal:
    """Annualised Sharpe from per-tick equity returns (assuming ~hourly ticks)."""
    if len(equity_series) < 2:
        return Decimal("0")

    returns: list[float] = []
    for i in range(1, len(equity_series)):
        prev = float(equity_series[i - 1])
        cur = float(equity_series[i])
        if prev != 0:
            returns.append((cur - prev) / prev)

    if not returns:
        return Decimal("0")

    mean_r = sum(returns) / len(returns)
    if len(returns) < 2:
        return Decimal("0")

    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance)

    if std_r == 0:
        return Decimal("0")

    # Annualise assuming ~hourly ticks, ~8760 ticks/year
    sharpe = (mean_r / std_r) * math.sqrt(min(len(returns), 8760))
    return Decimal(str(round(sharpe, 4)))


def _compute_max_drawdown(equity_series: list[Decimal]) -> Decimal:
    """Max drawdown as a positive percentage."""
    if len(equity_series) < 2:
        return Decimal("0")

    peak = equity_series[0]
    max_dd = Decimal("0")

    for eq in equity_series[1:]:
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak * Decimal("100")
            if dd > max_dd:
                max_dd = dd

    return Decimal(str(round(float(max_dd), 2)))


def _compute_trade_stats(
    fills: list[SimFillPayload],
) -> tuple[Decimal, Decimal, int]:
    """Compute win rate, profit factor, and trade count from fills.

    A "trade" is a round-trip: buy then sell (or the reverse).
    We track cumulative notional cost/proceeds to determine P&L
    when position flips or closes.
    """
    if not fills:
        return Decimal("0"), Decimal("0"), 0

    gross_profit = Decimal("0")
    gross_loss = Decimal("0")
    wins = 0
    total_trades = 0

    # Track cost basis for round-trip P&L
    position_qty = Decimal("0")
    cost_basis = Decimal("0")  # total cost of current position

    for fill in fills:
        qty = Decimal(fill.qty_base)
        price = Decimal(fill.price)
        notional = Decimal(fill.notional_quote)

        if fill.side == "buy":
            position_qty += qty
            cost_basis += notional
        else:  # sell
            if position_qty > 0:
                # Proportional cost basis for the sold portion
                sold_fraction = min(qty / position_qty, Decimal("1"))
                allocated_cost = cost_basis * sold_fraction
                pnl = notional - allocated_cost

                total_trades += 1
                if pnl > 0:
                    gross_profit += pnl
                    wins += 1
                else:
                    gross_loss += abs(pnl)

                cost_basis -= allocated_cost
                position_qty -= qty
                if position_qty < 0:
                    # Flipped to short — reset basis
                    cost_basis = abs(position_qty) * price
            else:
                total_trades += 1
                gross_loss += Decimal("0")

    win_rate = (
        Decimal(str(round(wins / total_trades * 100, 2))) if total_trades > 0 else Decimal("0")
    )
    profit_fac = (
        Decimal(str(round(float(gross_profit / gross_loss), 2)))
        if gross_loss > 0
        else Decimal("99.99")
        if gross_profit > 0
        else Decimal("0")
    )

    return win_rate, profit_fac, total_trades
