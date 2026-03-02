from __future__ import annotations

from decimal import Decimal

from fce.sim.engine import PortfolioState, rebalance_to_target_exposure


def test_rebalance_to_target_exposure_basic() -> None:
    state = PortfolioState(cash_quote=Decimal("1000"), positions_base={})
    fill = rebalance_to_target_exposure(
        state=state,
        market_id="m",
        price=Decimal("10"),
        target_exposure=Decimal("0.5"),
        fee_bps=Decimal("10"),
    )

    assert fill is not None
    assert fill.notional_quote == Decimal("500")
    assert fill.qty_base == Decimal("50")
    assert fill.fee_quote == Decimal("0.5")
    assert state.positions_base["m"] == Decimal("50")
    assert state.cash_quote == Decimal("499.5")
