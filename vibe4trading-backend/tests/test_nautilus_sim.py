from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from v4t.sim.nautilus_sim import NautilusPaperSim


def test_nautilus_paper_sim_rebalance_matches_fee_model() -> None:
    sim = NautilusPaperSim(
        market_id="spot:demo:DEMO",
        initial_equity_quote=Decimal("1000"),
        fee_bps=Decimal("10"),
    )
    try:
        fill = sim.rebalance_to_target_exposure(
            tick_time=datetime(2024, 1, 1, tzinfo=UTC),
            price=Decimal("10"),
            target_exposure=Decimal("0.5"),
        )
        assert fill is not None
        assert fill.notional_quote == Decimal("500.00000000")
        assert fill.qty_base == Decimal("50.00000000")
        assert fill.fee_quote == Decimal("0.50000000")

        assert sim.position_qty_base() == Decimal("50.00000000")
        assert sim.cash_quote() == Decimal("499.5")

        # Sell back to zero exposure.
        fill2 = sim.rebalance_to_target_exposure(
            tick_time=datetime(2024, 1, 1, 0, 1, tzinfo=UTC),
            price=Decimal("10"),
            target_exposure=Decimal("0"),
        )
        assert fill2 is not None
        assert fill2.notional_quote == Decimal("-500.00000000")
        assert fill2.qty_base == Decimal("-50.00000000")
        assert fill2.fee_quote == Decimal("0.50000000")

        assert sim.position_qty_base() == Decimal("0")
    finally:
        sim.close()
