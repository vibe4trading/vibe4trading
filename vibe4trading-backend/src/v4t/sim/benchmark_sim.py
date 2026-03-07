from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from v4t.benchmark.spec import PositionDirection, PositionMode
from v4t.contracts.numbers import decimal_to_str


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@dataclass(frozen=True)
class BenchmarkFill:
    market_id: str
    qty_base: Decimal
    price: Decimal
    notional_quote: Decimal
    fee_quote: Decimal
    reason: str | None = None
    position_mode: PositionMode = PositionMode.spot
    leverage: int = 1


@dataclass
class BenchmarkPosition:
    mode: PositionMode
    qty_base: Decimal
    entry_price: Decimal
    leverage: int
    margin_used: Decimal
    funding_cost_accumulated: Decimal = Decimal("0")
    stop_loss_pct: Decimal | None = None
    take_profit_pct: Decimal | None = None
    stop_loss_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    last_funding_time: datetime | None = None

    @property
    def direction(self) -> PositionDirection:
        if self.qty_base > 0:
            return PositionDirection.long
        if self.qty_base < 0:
            return PositionDirection.short
        return PositionDirection.flat


class BenchmarkPaperSim:
    def __init__(
        self,
        *,
        market_id: str,
        initial_equity_quote: Decimal,
        fee_bps: Decimal,
    ) -> None:
        self.market_id = market_id
        self.fee_bps = fee_bps
        self.cash_quote_value = initial_equity_quote
        self.position: BenchmarkPosition | None = None

    def close(self) -> None:
        return None

    def cash_quote(self) -> Decimal:
        return self.cash_quote_value

    def position_qty_base(self) -> Decimal:
        if self.position is None:
            return Decimal("0")
        return self.position.qty_base

    def position_mode(self) -> PositionMode | None:
        if self.position is None:
            return None
        return self.position.mode

    def position_direction(self) -> PositionDirection:
        if self.position is None:
            return PositionDirection.flat
        return self.position.direction

    def position_leverage(self) -> int:
        if self.position is None:
            return 1
        return self.position.leverage

    def entry_price(self) -> Decimal | None:
        if self.position is None:
            return None
        return self.position.entry_price

    def margin_used(self) -> Decimal:
        if self.position is None:
            return Decimal("0")
        return self.position.margin_used

    def liquidation_price(self) -> Decimal | None:
        if self.position is None or self.position.mode != PositionMode.futures:
            return None
        if self.position.leverage <= 0:
            return None
        if self.position.direction == PositionDirection.long:
            return self.position.entry_price * (
                Decimal("1") - (Decimal("1") / Decimal(self.position.leverage))
            )
        if self.position.direction == PositionDirection.short:
            return self.position.entry_price * (
                Decimal("1") + (Decimal("1") / Decimal(self.position.leverage))
            )
        return None

    def unrealized_pnl(self, *, price: Decimal) -> Decimal:
        if self.position is None:
            return Decimal("0")
        if self.position.mode == PositionMode.spot:
            return (price - self.position.entry_price) * self.position.qty_base
        return (price - self.position.entry_price) * self.position.qty_base

    def unrealized_pnl_pct(self, *, price: Decimal) -> Decimal:
        margin_used = self.margin_used()
        if margin_used == 0:
            return Decimal("0")
        return (self.unrealized_pnl(price=price) / margin_used) * Decimal("100")

    def equity_quote(self, *, price: Decimal) -> Decimal:
        if self.position is None:
            return self.cash_quote_value
        if self.position.mode == PositionMode.spot:
            return self.cash_quote_value + (self.position.qty_base * price)
        return self.cash_quote_value + self.position.margin_used + self.unrealized_pnl(price=price)

    def funding_cost_accumulated(self) -> Decimal:
        if self.position is None:
            return Decimal("0")
        return self.position.funding_cost_accumulated

    def trigger_prices(self) -> tuple[Decimal | None, Decimal | None]:
        if self.position is None:
            return None, None
        return self.position.stop_loss_price, self.position.take_profit_price

    def portfolio_view(self, *, price: Decimal) -> dict[str, str]:
        stop_loss_price, take_profit_price = self.trigger_prices()
        position_mode = self.position_mode()
        return {
            "equity_quote": decimal_to_str(self.equity_quote(price=price)),
            "cash_quote": decimal_to_str(self.cash_quote()),
            "position_mode": position_mode.value if position_mode is not None else "none",
            "position_direction": self.position_direction().value,
            "position_qty_base": decimal_to_str(self.position_qty_base()),
            "position_leverage": str(self.position_leverage()),
            "entry_price": decimal_to_str(self.entry_price())
            if self.entry_price() is not None
            else "n/a",
            "current_price": decimal_to_str(price),
            "liquidation_price": decimal_to_str(self.liquidation_price())
            if self.liquidation_price() is not None
            else "n/a",
            "unrealized_pnl": decimal_to_str(self.unrealized_pnl(price=price)),
            "unrealized_pnl_pct": decimal_to_str(self.unrealized_pnl_pct(price=price)),
            "funding_cost_accumulated": decimal_to_str(self.funding_cost_accumulated()),
            "stop_loss_price": decimal_to_str(stop_loss_price)
            if stop_loss_price is not None
            else "n/a",
            "take_profit_price": decimal_to_str(take_profit_price)
            if take_profit_price is not None
            else "n/a",
            "price": decimal_to_str(price),
        }

    def apply_funding_rate(
        self,
        *,
        tick_time: datetime,
        price: Decimal,
        funding_rate: Decimal,
    ) -> Decimal:
        if self.position is None or self.position.mode != PositionMode.futures:
            return Decimal("0")
        direction_sign = Decimal("1") if self.position.qty_base > 0 else Decimal("-1")
        notional = abs(self.position.qty_base) * price
        funding_cost = notional * funding_rate * direction_sign
        self.cash_quote_value -= funding_cost
        self.position.funding_cost_accumulated += funding_cost
        self.position.last_funding_time = _as_utc(tick_time)
        return funding_cost

    def maybe_apply_default_funding(
        self,
        *,
        tick_time: datetime,
        price: Decimal,
        funding_rate: Decimal = Decimal("0"),
    ) -> Decimal:
        if self.position is None or self.position.mode != PositionMode.futures:
            return Decimal("0")
        tick_time = _as_utc(tick_time)
        if self.position.last_funding_time is None:
            self.position.last_funding_time = tick_time
            return Decimal("0")
        if tick_time - self.position.last_funding_time < timedelta(hours=8):
            return Decimal("0")
        return self.apply_funding_rate(tick_time=tick_time, price=price, funding_rate=funding_rate)

    def process_price_update(
        self,
        *,
        tick_time: datetime,
        price: Decimal,
    ) -> BenchmarkFill | None:
        if self.position is None:
            return None

        if self.position.mode == PositionMode.futures:
            liq = self.liquidation_price()
            if liq is not None:
                if self.position.qty_base > 0 and price <= liq:
                    return self._liquidate(price=price)
                if self.position.qty_base < 0 and price >= liq:
                    return self._liquidate(price=price)

        stop_loss_price = self.position.stop_loss_price
        take_profit_price = self.position.take_profit_price
        if stop_loss_price is not None:
            if self.position.qty_base > 0 and price <= stop_loss_price:
                return self._close_position(price=price, reason="stop_loss")
            if self.position.qty_base < 0 and price >= stop_loss_price:
                return self._close_position(price=price, reason="stop_loss")
        if take_profit_price is not None:
            if self.position.qty_base > 0 and price >= take_profit_price:
                return self._close_position(price=price, reason="take_profit")
            if self.position.qty_base < 0 and price <= take_profit_price:
                return self._close_position(price=price, reason="take_profit")
        return None

    def rebalance_to_target(
        self,
        *,
        tick_time: datetime,
        price: Decimal,
        target_exposure: Decimal,
        mode: PositionMode,
        leverage: int,
        stop_loss_pct: Decimal | None,
        take_profit_pct: Decimal | None,
        reason: str | None = None,
    ) -> list[BenchmarkFill]:
        _ = _as_utc(tick_time)
        if price == 0:
            return []

        if target_exposure == 0:
            close_fill = self._close_position(price=price, reason=reason or "close")
            return [close_fill] if close_fill is not None else []

        fills: list[BenchmarkFill] = []
        if self.position is not None and self.position.mode != mode:
            close_fill = self._close_position(price=price, reason="mode_switch")
            if close_fill is not None:
                fills.append(close_fill)

        if mode == PositionMode.spot:
            open_fill = self._rebalance_spot(
                price=price,
                target_exposure=target_exposure,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                reason=reason,
            )
        else:
            open_fill = self._rebalance_futures(
                price=price,
                target_exposure=target_exposure,
                leverage=leverage,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                reason=reason,
            )
        if open_fill is not None:
            fills.append(open_fill)
        return fills

    def _fee(self, notional_quote: Decimal) -> Decimal:
        return (abs(notional_quote) * self.fee_bps) / Decimal("10000")

    def _set_triggers(
        self,
        position: BenchmarkPosition,
        *,
        stop_loss_pct: Decimal | None,
        take_profit_pct: Decimal | None,
    ) -> None:
        position.stop_loss_pct = stop_loss_pct
        position.take_profit_pct = take_profit_pct
        if stop_loss_pct is None:
            position.stop_loss_price = None
        elif position.direction == PositionDirection.long:
            position.stop_loss_price = position.entry_price * (
                Decimal("1") - (stop_loss_pct / Decimal("100"))
            )
        else:
            position.stop_loss_price = position.entry_price * (
                Decimal("1") + (stop_loss_pct / Decimal("100"))
            )

        if take_profit_pct is None:
            position.take_profit_price = None
        elif position.direction == PositionDirection.long:
            position.take_profit_price = position.entry_price * (
                Decimal("1") + (take_profit_pct / Decimal("100"))
            )
        else:
            position.take_profit_price = position.entry_price * (
                Decimal("1") - (take_profit_pct / Decimal("100"))
            )

    def _rebalance_spot(
        self,
        *,
        price: Decimal,
        target_exposure: Decimal,
        stop_loss_pct: Decimal | None,
        take_profit_pct: Decimal | None,
        reason: str | None,
    ) -> BenchmarkFill | None:
        current_qty = self.position.qty_base if self.position is not None else Decimal("0")
        equity = self.equity_quote(price=price)
        target_qty = (target_exposure * equity) / price
        delta_qty = target_qty - current_qty
        if delta_qty == 0:
            return None

        notional = delta_qty * price
        fee = self._fee(notional)
        self.cash_quote_value -= notional + fee

        new_qty = current_qty + delta_qty
        if new_qty == 0:
            self.position = None
        else:
            if (
                self.position is not None
                and current_qty != 0
                and (current_qty > 0) == (new_qty > 0)
            ):
                old_entry = self.position.entry_price
                new_entry = (abs(current_qty) * old_entry + abs(delta_qty) * price) / abs(new_qty)
            else:
                new_entry = price
            self.position = BenchmarkPosition(
                mode=PositionMode.spot,
                qty_base=new_qty,
                entry_price=new_entry,
                leverage=1,
                margin_used=Decimal("0"),
            )
            self._set_triggers(
                self.position,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
            )

        return BenchmarkFill(
            market_id=self.market_id,
            qty_base=delta_qty,
            price=price,
            notional_quote=notional,
            fee_quote=fee,
            reason=reason,
            position_mode=PositionMode.spot,
            leverage=1,
        )

    def _rebalance_futures(
        self,
        *,
        price: Decimal,
        target_exposure: Decimal,
        leverage: int,
        stop_loss_pct: Decimal | None,
        take_profit_pct: Decimal | None,
        reason: str | None,
    ) -> BenchmarkFill | None:
        equity = self.equity_quote(price=price)
        target_qty = (target_exposure * equity) / price
        current_qty = self.position.qty_base if self.position is not None else Decimal("0")
        delta_qty = target_qty - current_qty
        if delta_qty == 0 and self.position is not None:
            self.position.leverage = leverage
            self._set_triggers(
                self.position,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
            )
            return None

        if self.position is not None and current_qty != 0 and (current_qty > 0) != (target_qty > 0):
            self._close_position(price=price, reason="flip")
            current_qty = Decimal("0")
            delta_qty = target_qty - current_qty

        elif self.position is not None and current_qty != 0 and abs(target_qty) < abs(current_qty):
            reduce_qty = current_qty - target_qty
            close_qty = -reduce_qty
            avg_entry = self.position.entry_price
            realized = (price - avg_entry) * reduce_qty
            old_margin = self.position.margin_used
            remaining_qty = target_qty
            remaining_notional = abs(remaining_qty) * price
            remaining_margin = (
                remaining_notional / Decimal(leverage) if remaining_qty != 0 else Decimal("0")
            )
            released_margin = max(Decimal("0"), old_margin - remaining_margin)
            fee = self._fee(close_qty * price)
            self.cash_quote_value += realized + released_margin - fee
            if remaining_qty == 0:
                self.position = None
            else:
                self.position = BenchmarkPosition(
                    mode=PositionMode.futures,
                    qty_base=remaining_qty,
                    entry_price=avg_entry,
                    leverage=leverage,
                    margin_used=remaining_margin,
                    funding_cost_accumulated=self.position.funding_cost_accumulated,
                    last_funding_time=self.position.last_funding_time,
                )
                self._set_triggers(
                    self.position,
                    stop_loss_pct=stop_loss_pct,
                    take_profit_pct=take_profit_pct,
                )
            return BenchmarkFill(
                market_id=self.market_id,
                qty_base=close_qty,
                price=price,
                notional_quote=close_qty * price,
                fee_quote=fee,
                reason=reason or "rebalance",
                position_mode=PositionMode.futures,
                leverage=leverage,
            )

        target_notional = abs(target_qty) * price
        margin_required = target_notional / Decimal(leverage)
        current_margin = self.position.margin_used if self.position is not None else Decimal("0")

        extending = (
            self.position is not None
            and self.position.qty_base != 0
            and (self.position.qty_base > 0) == (target_qty > 0)
        )

        if extending:
            assert self.position is not None
            old_entry = self.position.entry_price
            new_entry = (abs(current_qty) * old_entry + abs(delta_qty) * price) / abs(target_qty)
        else:
            new_entry = price

        if not extending and self.position is not None and self.position.qty_base != 0:
            unrealized = (price - self.position.entry_price) * self.position.qty_base
            self.cash_quote_value += unrealized

        margin_delta = margin_required - current_margin
        fee = self._fee(delta_qty * price)
        if self.cash_quote_value - margin_delta - fee < 0:
            if not extending and self.position is not None and self.position.qty_base != 0:
                unrealized = (price - self.position.entry_price) * self.position.qty_base
                self.cash_quote_value -= unrealized
            return None
        self.cash_quote_value -= margin_delta + fee
        funding_cost = (
            self.position.funding_cost_accumulated if self.position is not None else Decimal("0")
        )
        last_funding_time = self.position.last_funding_time if self.position is not None else None
        self.position = BenchmarkPosition(
            mode=PositionMode.futures,
            qty_base=target_qty,
            entry_price=new_entry,
            leverage=leverage,
            margin_used=margin_required,
            funding_cost_accumulated=funding_cost,
            last_funding_time=last_funding_time,
        )
        self._set_triggers(
            self.position,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
        )
        return BenchmarkFill(
            market_id=self.market_id,
            qty_base=delta_qty,
            price=price,
            notional_quote=delta_qty * price,
            fee_quote=fee,
            reason=reason,
            position_mode=PositionMode.futures,
            leverage=leverage,
        )

    def _close_position(self, *, price: Decimal, reason: str | None) -> BenchmarkFill | None:
        if self.position is None or self.position.qty_base == 0:
            self.position = None
            return None

        qty = -self.position.qty_base
        notional = qty * price
        fee = self._fee(notional)
        if self.position.mode == PositionMode.spot:
            self.cash_quote_value -= notional + fee
        else:
            realized = (price - self.position.entry_price) * self.position.qty_base
            self.cash_quote_value += self.position.margin_used + realized - fee
        fill = BenchmarkFill(
            market_id=self.market_id,
            qty_base=qty,
            price=price,
            notional_quote=notional,
            fee_quote=fee,
            reason=reason,
            position_mode=self.position.mode,
            leverage=self.position.leverage,
        )
        self.position = None
        return fill

    def _liquidate(self, *, price: Decimal) -> BenchmarkFill | None:
        if self.position is None:
            return None
        qty = -self.position.qty_base
        fill = BenchmarkFill(
            market_id=self.market_id,
            qty_base=qty,
            price=price,
            notional_quote=qty * price,
            fee_quote=Decimal("0"),
            reason="liquidation",
            position_mode=self.position.mode,
            leverage=self.position.leverage,
        )
        self.position = None
        return fill
