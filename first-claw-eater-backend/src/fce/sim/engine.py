from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Fill:
    market_id: str
    qty_base: Decimal
    price: Decimal
    notional_quote: Decimal
    fee_quote: Decimal


@dataclass
class PortfolioState:
    cash_quote: Decimal
    positions_base: dict[str, Decimal]

    def position_qty(self, market_id: str) -> Decimal:
        return self.positions_base.get(market_id, Decimal("0"))

    def equity_quote(self, *, market_id: str, price: Decimal) -> Decimal:
        return self.cash_quote + (self.position_qty(market_id) * price)


def rebalance_to_target_exposure(
    *,
    state: PortfolioState,
    market_id: str,
    price: Decimal,
    target_exposure: Decimal,
    fee_bps: Decimal,
) -> Fill | None:
    """Rebalance spot position to target exposure (fraction of equity).

    target_exposure is clamped/validated upstream; this function assumes spot long-only.
    """

    equity = state.equity_quote(market_id=market_id, price=price)
    target_notional = target_exposure * equity
    current_notional = state.position_qty(market_id) * price
    delta_notional = target_notional - current_notional

    if delta_notional == 0:
        return None

    delta_qty = (delta_notional / price) if price != 0 else Decimal("0")
    fee = (abs(delta_notional) * fee_bps) / Decimal("10000")

    # Cash decreases on buys (delta_notional>0), increases on sells.
    state.cash_quote = state.cash_quote - delta_notional - fee
    state.positions_base[market_id] = state.position_qty(market_id) + delta_qty

    return Fill(
        market_id=market_id,
        qty_base=delta_qty,
        price=price,
        notional_quote=delta_notional,
        fee_quote=fee,
    )
