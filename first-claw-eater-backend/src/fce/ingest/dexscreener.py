from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from fce.settings import get_settings


class DexScreenerPair(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    chain_id: str = Field(alias="chainId")
    dex_id: str = Field(alias="dexId")
    pair_address: str = Field(alias="pairAddress")

    price_native: str = Field(alias="priceNative")
    price_usd: str | None = Field(default=None, alias="priceUsd")


class DexScreenerPairsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pairs: list[DexScreenerPair] | None = None


@dataclass(frozen=True)
class DexScreenerResolvedSpot:
    market_id: str
    base_price: Decimal


def resolve_spot_market(*, chain_id: str, pair_id: str) -> DexScreenerResolvedSpot:
    """Resolve a DexScreener pair into our MVP spot market_id + base price.

    Note: DexScreener's free API does not provide historical candles; we use the
    resolved price as a seed for a deterministic synthetic backfill.
    """

    settings = get_settings()
    base_url = settings.dexscreener_base_url.rstrip("/")
    url = f"{base_url}/latest/dex/pairs/{chain_id}/{pair_id}"

    with httpx.Client(timeout=float(settings.dexscreener_timeout_seconds)) as client:
        r = client.get(url)
        r.raise_for_status()
        data: dict[str, Any] = r.json()

    resp = DexScreenerPairsResponse.model_validate(data)
    if not resp.pairs:
        raise ValueError("DexScreener returned no pairs")

    pair = resp.pairs[0]
    market_id = f"spot:{pair.dex_id}:{pair.pair_address}"

    raw_price = pair.price_usd or pair.price_native
    if raw_price is None:
        raise ValueError("DexScreener pair missing price")

    return DexScreenerResolvedSpot(market_id=market_id, base_price=Decimal(str(raw_price)))
