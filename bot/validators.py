from __future__ import annotations

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}  # expandable
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK"}


def validate_symbol(symbol: str) -> str:
    """Validates and normalises the trading symbol."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string (e.g. BTCUSDT).")
    cleaned = symbol.strip().upper()
    if len(cleaned) < 3:
        raise ValueError(f"Symbol '{cleaned}' is too short to be valid.")
    # Futures symbols are alphanumeric only (no slashes)
    if not cleaned.isalnum():
        raise ValueError(
            f"Symbol '{cleaned}' contains invalid characters. "
            "Use format like BTCUSDT (no slashes or spaces)."
        )
    return cleaned


def validate_side(side: str) -> str:
    """Validates order side (BUY or SELL)."""
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValueError(
            f"Side '{cleaned}' is invalid. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return cleaned


def validate_order_type(order_type: str) -> str:
    """Validates order type."""
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type '{cleaned}' is invalid. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return cleaned


def validate_quantity(quantity: str | float) -> float:
    """Validates that quantity is a positive number."""
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0. Got: {qty}.")
    return qty


def validate_price(price: str | float | None, order_type: str) -> float | None:
    """
    Validates price based on order type.
    - MARKET orders: price must be None/omitted
    - LIMIT orders: price must be a positive number
    """
    if order_type == "MARKET":
        if price is not None:
            raise ValueError("Price must not be provided for MARKET orders.")
        return None

    if order_type in ("LIMIT", "STOP_MARKET"):
        if price is None:
            raise ValueError(f"Price is required for {order_type} orders.")
        try:
            p = float(price)
        except (TypeError, ValueError):
            raise ValueError(f"Price '{price}' is not a valid number.")
        if p <= 0:
            raise ValueError(f"Price must be greater than 0. Got: {p}.")
        return p

    return None  # for unrecognized types, let API reject


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
) -> dict:
    """
    Master validation function. Validates all parameters together and
    returns a cleaned dict ready for use in the order payload.

    Raises ValueError with a descriptive message on any invalid input.
    """
    validated_symbol = validate_symbol(symbol)
    validated_side = validate_side(side)
    validated_type = validate_order_type(order_type)
    validated_qty = validate_quantity(quantity)
    validated_price = validate_price(price, validated_type)

    result = {
        "symbol": validated_symbol,
        "side": validated_side,
        "order_type": validated_type,
        "quantity": validated_qty,
    }
    if validated_price is not None:
        result["price"] = validated_price

    return result
