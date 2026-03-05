from __future__ import annotations

import pytest
from pydantic import ValidationError

from v4t.contracts.ids import AssetRef, MarketRef, MarketType, TokenRef, asset_id, market_id


def test_asset_ref_valid() -> None:
    asset = AssetRef(namespace="demo", id="BTC", symbol="Bitcoin")
    assert asset.namespace == "demo"
    assert asset.id == "BTC"
    assert asset.symbol == "Bitcoin"


def test_asset_ref_without_symbol() -> None:
    asset = AssetRef(namespace="demo", id="BTC")
    assert asset.symbol is None


def test_asset_ref_empty_namespace_fails() -> None:
    with pytest.raises(ValidationError):
        AssetRef(namespace="", id="BTC")


def test_asset_ref_empty_id_fails() -> None:
    with pytest.raises(ValidationError):
        AssetRef(namespace="demo", id="")


def test_token_ref_valid() -> None:
    token = TokenRef(chain="ethereum", address="0x123", symbol="USDC")
    assert token.chain == "ethereum"
    assert token.address == "0x123"


def test_market_ref_valid() -> None:
    base = AssetRef(namespace="demo", id="BTC")
    quote = AssetRef(namespace="demo", id="USD")
    market = MarketRef(
        venue="demo",
        market_type=MarketType.spot,
        base=base,
        quote=quote,
        instrument_id="BTC-USD",
    )
    assert market.venue == "demo"
    assert market.market_type == MarketType.spot


def test_asset_id_codec() -> None:
    asset = AssetRef(namespace="demo", id="BTC")
    assert asset_id(asset) == "demo:BTC"


def test_market_id_codec() -> None:
    base = AssetRef(namespace="demo", id="BTC")
    quote = AssetRef(namespace="demo", id="USD")
    market = MarketRef(
        venue="demo",
        market_type=MarketType.spot,
        base=base,
        quote=quote,
        instrument_id="BTC-USD",
    )
    assert market_id(market) == "spot:demo:BTC-USD"


def test_market_ref_frozen() -> None:
    base = AssetRef(namespace="demo", id="BTC")
    quote = AssetRef(namespace="demo", id="USD")
    market = MarketRef(
        venue="demo",
        market_type=MarketType.spot,
        base=base,
        quote=quote,
        instrument_id="BTC-USD",
    )
    with pytest.raises(ValidationError):
        market.venue = "other"
