from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MarketType(StrEnum):
    spot = "spot"
    perps = "perps"


class AssetRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: str = Field(min_length=1)
    id: str = Field(min_length=1)
    symbol: str | None = None


class TokenRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    chain: str = Field(min_length=1)
    address: str = Field(min_length=1)
    symbol: str | None = None


class MarketRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue: str = Field(min_length=1)
    market_type: MarketType
    base: AssetRef
    quote: AssetRef
    instrument_id: str = Field(min_length=1)


def asset_id(asset: AssetRef) -> str:
    return f"{asset.namespace}:{asset.id}"


def market_id(market: MarketRef) -> str:
    return f"{market.market_type}:{market.venue}:{market.instrument_id}"
