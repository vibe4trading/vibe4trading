from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from v4t.contracts.numbers import DecimalString, decimal_to_str, parse_decimal


def test_parse_decimal_from_decimal() -> None:
    result = parse_decimal(Decimal("123.45"))
    assert result == Decimal("123.45")


def test_parse_decimal_from_int() -> None:
    result = parse_decimal(100)
    assert result == Decimal("100")


def test_parse_decimal_from_float() -> None:
    result = parse_decimal(123.45)
    assert result == Decimal("123.45")


def test_parse_decimal_from_string() -> None:
    result = parse_decimal("123.45")
    assert result == Decimal("123.45")


def test_parse_decimal_invalid_type() -> None:
    with pytest.raises(TypeError):
        parse_decimal([1, 2, 3])


def test_decimal_to_str_basic() -> None:
    result = decimal_to_str(Decimal("123.45"))
    assert result == "123.45"


def test_decimal_to_str_no_exponent() -> None:
    result = decimal_to_str(Decimal("0.0001"))
    assert result == "0.0001"
    assert "e" not in result.lower()


def test_decimal_string_valid() -> None:
    ds = DecimalString(value="123.45")
    assert ds.value == "123.45"


def test_decimal_string_negative() -> None:
    ds = DecimalString(value="-123.45")
    assert ds.value == "-123.45"


def test_decimal_string_invalid_pattern() -> None:
    with pytest.raises(ValidationError):
        DecimalString(value="abc")
