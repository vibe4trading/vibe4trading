from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from v4t.benchmark.spec import PositionMode
from v4t.sim.benchmark_sim import BenchmarkPaperSim


def test_benchmark_sim_futures_take_profit_and_funding() -> None:
    sim = BenchmarkPaperSim(
        market_id="spot:test:BTC",
        initial_equity_quote=Decimal("1000"),
        fee_bps=Decimal("10"),
    )
    try:
        fills = sim.rebalance_to_target(
            tick_time=datetime(2024, 1, 1, tzinfo=UTC),
            price=Decimal("100"),
            target_exposure=Decimal("1.5"),
            mode=PositionMode.futures,
            leverage=2,
            stop_loss_pct=Decimal("5"),
            take_profit_pct=Decimal("10"),
        )
        assert len(fills) == 1
        opened = fills[0]
        assert opened.position_mode == PositionMode.futures
        assert sim.position_qty_base() == Decimal("15.0")
        assert sim.position_leverage() == 2
        assert sim.liquidation_price() == Decimal("50.0")

        funding = sim.apply_funding_rate(
            tick_time=datetime(2024, 1, 1, 8, tzinfo=UTC),
            price=Decimal("100"),
            funding_rate=Decimal("0.001"),
        )
        assert funding == Decimal("1.5000")

        tp_fill = sim.process_price_update(
            tick_time=datetime(2024, 1, 1, 9, tzinfo=UTC),
            price=Decimal("110"),
        )
        assert tp_fill is not None
        assert tp_fill.reason == "take_profit"
        assert sim.position_qty_base() == Decimal("0")
    finally:
        sim.close()


def test_benchmark_sim_short_liquidation() -> None:
    sim = BenchmarkPaperSim(
        market_id="spot:test:BTC",
        initial_equity_quote=Decimal("1000"),
        fee_bps=Decimal("10"),
    )
    try:
        fills = sim.rebalance_to_target(
            tick_time=datetime(2024, 1, 1, tzinfo=UTC),
            price=Decimal("100"),
            target_exposure=Decimal("-2.5"),
            mode=PositionMode.futures,
            leverage=3,
            stop_loss_pct=Decimal("5"),
            take_profit_pct=None,
        )
        assert len(fills) == 1
        assert sim.position_qty_base() < 0
        assert sim.liquidation_price() == Decimal("133.3333333333333333333333333")

        liq_fill = sim.process_price_update(
            tick_time=datetime(2024, 1, 1, 1, tzinfo=UTC),
            price=Decimal("140"),
        )
        assert liq_fill is not None
        assert liq_fill.reason == "liquidation"
        assert sim.position_qty_base() == Decimal("0")
    finally:
        sim.close()


def test_benchmark_sim_flip_only_charges_open_leg_after_close() -> None:
    sim = BenchmarkPaperSim(
        market_id="spot:test:BTC",
        initial_equity_quote=Decimal("1000"),
        fee_bps=Decimal("10"),
    )
    try:
        first_fills = sim.rebalance_to_target(
            tick_time=datetime(2024, 1, 1, tzinfo=UTC),
            price=Decimal("100"),
            target_exposure=Decimal("1"),
            mode=PositionMode.futures,
            leverage=2,
            stop_loss_pct=None,
            take_profit_pct=None,
        )
        assert len(first_fills) == 1

        cash_before_flip = sim.cash_quote()
        flip_fills = sim.rebalance_to_target(
            tick_time=datetime(2024, 1, 1, 1, tzinfo=UTC),
            price=Decimal("100"),
            target_exposure=Decimal("-0.5"),
            mode=PositionMode.futures,
            leverage=2,
            stop_loss_pct=None,
            take_profit_pct=None,
        )
        assert len(flip_fills) == 1
        flip_fill = flip_fills[0]
        assert flip_fill.qty_base < 0
        assert flip_fill.fee_quote == Decimal("0.4995")
        assert sim.cash_quote() > cash_before_flip
    finally:
        sim.close()
