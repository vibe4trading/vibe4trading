from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DECIMAL_STR_RE = r"^-?\d+(\.\d+)?$"


def parse_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # JSON numbers arrive as floats; convert via str() to avoid binary float artifacts.
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value)
    raise TypeError(f"Unsupported decimal type: {type(value)}")


def decimal_to_str(value: Decimal) -> str:
    # Avoid exponent notation; store as a plain string for canonical event payloads.
    return format(value, "f")


class DecimalString(BaseModel):
    """A small helper for docs/validation of canonical decimal-string encoding."""

    model_config = ConfigDict(frozen=True)

    value: str = Field(pattern=DECIMAL_STR_RE)
