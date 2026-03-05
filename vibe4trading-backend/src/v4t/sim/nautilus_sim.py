from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.common.config import LoggingConfig
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.messages import SubmitOrder
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import (
    ClientOrderId,
    InstrumentId,
    StrategyId,
    Symbol,
    Venue,
)
from nautilus_trader.model.instruments.currency_pair import CurrencyPair
from nautilus_trader.model.objects import Currency, Money, Price, Quantity
from nautilus_trader.model.orders.market import MarketOrder


@dataclass(frozen=True)
class NautilusFill:
    market_id: str
    qty_base: Decimal
    price: Decimal
    notional_quote: Decimal
    fee_quote: Decimal


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _to_unix_nanos(dt: datetime) -> int:
    # Nautilus' dt_to_unix_nanos type hints don't accept datetime, but runtime does.
    # Use an ISO-8601 string so pyright stays happy.
    return int(dt_to_unix_nanos(_as_utc(dt).isoformat()))


def _quantize_decimal(value: Decimal, *, precision: int) -> Decimal:
    if precision <= 0:
        return value.quantize(Decimal("1"))
    exp = Decimal(1).scaleb(-precision)  # 10^-precision
    return value.quantize(exp)


class NautilusPaperSim:
    """Single-market paper portfolio backed by Nautilus Trader.

    The orchestrator stays responsible for:
    - scheduling ticks and calling the LLM
    - converting target exposures -> desired position deltas

    Nautilus is responsible for:
    - applying fills + fees and tracking cash/positions deterministically
    """

    def __init__(
        self,
        *,
        market_id: str,
        initial_equity_quote: Decimal,
        fee_bps: Decimal,
        quote_currency_code: str = "USDC",
        price_precision: int = 6,
        size_precision: int = 8,
    ) -> None:
        self.market_id = market_id
        self.price_precision = int(price_precision)
        self.size_precision = int(size_precision)

        # Used before the first engine tick starts (when no account exists yet).
        self._starting_cash_quote = initial_equity_quote

        self.venue = Venue("V4T")
        self.instrument_id = InstrumentId(symbol=Symbol(market_id), venue=self.venue)
        self.strategy_id = StrategyId("V4T-STRAT-001")

        self.quote_currency = Currency.from_str(quote_currency_code)
        # Keep a stable, unique currency code (market_id is already unique).
        self.base_currency = Currency.from_str(market_id)

        self._order_seq = 0
        self._closed = False

        fee_rate = fee_bps / Decimal("10000")

        # Bypass Nautilus stdout logging to keep worker logs clean.
        engine_cfg = BacktestEngineConfig(
            logging=LoggingConfig(bypass_logging=True),
            run_analysis=False,
        )
        self.engine = BacktestEngine(engine_cfg)
        self.engine.add_venue(
            venue=self.venue,
            oms_type=OmsType.NETTING,
            account_type=AccountType.CASH,
            starting_balances=[Money.from_decimal(initial_equity_quote, self.quote_currency)],
            base_currency=None,
            # Process trading commands immediately at the current tick.
            use_message_queue=False,
        )

        # A minimal CurrencyPair instrument is enough for spot-style accounting.
        instrument = CurrencyPair(
            instrument_id=self.instrument_id,
            raw_symbol=Symbol(market_id),
            base_currency=self.base_currency,
            quote_currency=self.quote_currency,
            price_precision=self.price_precision,
            size_precision=self.size_precision,
            price_increment=Price(
                Decimal(1).scaleb(-self.price_precision), precision=self.price_precision
            ),
            size_increment=Quantity(
                Decimal(1).scaleb(-self.size_precision), precision=self.size_precision
            ),
            lot_size=None,
            max_quantity=Quantity.from_int(1_000_000_000),
            min_quantity=Quantity(
                Decimal(1).scaleb(-self.size_precision), precision=self.size_precision
            ),
            max_notional=None,
            min_notional=Money(0.0, self.quote_currency),
            max_price=Price(1_000_000_000, precision=self.price_precision),
            min_price=Price(
                Decimal(1).scaleb(-self.price_precision), precision=self.price_precision
            ),
            margin_init=Decimal(0),
            margin_maint=Decimal(0),
            maker_fee=fee_rate,
            taker_fee=fee_rate,
            ts_event=0,
            ts_init=0,
        )
        self.engine.add_instrument(instrument)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.engine.end()
        except Exception:
            # Best-effort cleanup.
            pass
        try:
            self.engine.dispose()
        except Exception:
            pass

    def _process_quote_tick(self, *, tick_time: datetime, price: Decimal) -> None:
        tick_time = _as_utc(tick_time)
        price = _quantize_decimal(price, precision=self.price_precision)
        price_str = format(price, "f")
        ts = _to_unix_nanos(tick_time)

        qt = QuoteTick(
            self.instrument_id,
            Price.from_str(price_str),
            Price.from_str(price_str),
            Quantity(1_000_000_000, precision=self.size_precision),
            Quantity(1_000_000_000, precision=self.size_precision),
            ts,
            ts,
        )
        self.engine.add_data([qt])
        self.engine.run(streaming=True)
        self.engine.clear_data()

    def position_qty_base(self) -> Decimal:
        return self.engine.kernel.portfolio.net_position(self.instrument_id)

    def cash_quote(self) -> Decimal:
        acc = self.engine.kernel.portfolio.account(self.venue)
        if acc is None:
            return self._starting_cash_quote
        bal = acc.balances().get(self.quote_currency)
        if bal is None:
            return Decimal("0")
        return bal.total.as_decimal()

    def equity_quote(self, *, price: Decimal) -> Decimal:
        return self.cash_quote() + (self.position_qty_base() * price)

    def rebalance_to_target_exposure(
        self,
        *,
        tick_time: datetime,
        price: Decimal,
        target_exposure: Decimal,
    ) -> NautilusFill | None:
        """Rebalance spot position to target exposure (fraction of equity)."""

        if price == 0:
            return None

        # Ensure Nautilus kernel clock + caches are updated to this tick.
        self._process_quote_tick(tick_time=tick_time, price=price)

        pre_pos = self.position_qty_base()
        pre_cash = self.cash_quote()
        equity = pre_cash + (pre_pos * price)

        target_notional = target_exposure * equity
        current_notional = pre_pos * price
        delta_notional = target_notional - current_notional

        if delta_notional == 0:
            return None

        delta_qty = delta_notional / price
        if delta_qty == 0:
            return None

        order_side = OrderSide.BUY if delta_qty > 0 else OrderSide.SELL
        order_qty = _quantize_decimal(abs(delta_qty), precision=self.size_precision)
        if order_qty == 0:
            return None

        self._order_seq += 1
        ts = _to_unix_nanos(tick_time)

        order = MarketOrder(
            self.engine.kernel.trader_id,
            self.strategy_id,
            self.instrument_id,
            ClientOrderId(f"V4T-{self._order_seq}"),
            order_side,
            Quantity.from_decimal(order_qty),
            UUID4(),
            ts,
        )
        cmd = SubmitOrder(
            self.engine.kernel.trader_id,
            self.strategy_id,
            order,
            UUID4(),
            ts,
        )
        self.engine.kernel.exec_engine.execute(cmd)

        post_pos = self.position_qty_base()
        post_cash = self.cash_quote()

        qty_base = post_pos - pre_pos
        if qty_base == 0:
            return None

        notional_quote = qty_base * price
        quote_delta = post_cash - pre_cash
        fee_quote = (-notional_quote) - quote_delta

        return NautilusFill(
            market_id=self.market_id,
            qty_base=qty_base,
            price=price,
            notional_quote=notional_quote,
            fee_quote=fee_quote,
        )
