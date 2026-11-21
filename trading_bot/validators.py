"""Validation and normalization for order inputs."""

import re
from decimal import Decimal, InvalidOperation

from .exceptions import ValidationError

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,30}$")


def validate_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not _SYMBOL_RE.fullmatch(normalized):
        raise ValidationError(
            "Invalid symbol. Use 2-30 uppercase letters/numbers, for example BTCUSDT."
        )
    return normalized


def validate_side(side: str) -> str:
    normalized = side.strip().upper()
    if normalized not in {"BUY", "SELL"}:
        raise ValidationError("Side must be BUY or SELL.")
    return normalized


def validate_order_type(order_type: str) -> str:
    normalized = order_type.strip().upper()
    if normalized not in {"MARKET", "LIMIT"}:
        raise ValidationError("Order type must be MARKET or LIMIT.")
    return normalized


def _positive_decimal(value: str | int | float | Decimal, field_name: str) -> Decimal:
    try:
        # str() avoids importing binary float artifacts into Decimal.
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        raise ValidationError(f"{field_name} must be a valid number.") from None

    if not parsed.is_finite() or parsed <= 0:
        raise ValidationError(f"{field_name} must be a finite number greater than zero.")
    return parsed


def decimal_to_api_string(value: Decimal) -> str:
    """Render a Decimal without exponent notation or unnecessary trailing zeros."""
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def validate_quantity(quantity: str | int | float | Decimal) -> str:
    return decimal_to_api_string(_positive_decimal(quantity, "Quantity"))


def validate_price(price: str | int | float | Decimal | None) -> str:
    if price is None:
        raise ValidationError("Price is required for a LIMIT order.")
    return decimal_to_api_string(_positive_decimal(price, "Price"))


def validate_order(
    *, symbol: str, side: str, order_type: str,
    quantity: str | int | float | Decimal,
    price: str | int | float | Decimal | None = None,
) -> dict[str, str]:
    """Validate an order and return normalized fields ready for the API."""
    normalized_type = validate_order_type(order_type)
    result = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "type": normalized_type,
        "quantity": validate_quantity(quantity),
    }

    if normalized_type == "LIMIT":
        result["price"] = validate_price(price)
    elif price is not None:
        raise ValidationError("Do not provide --price for a MARKET order.")

    return result
