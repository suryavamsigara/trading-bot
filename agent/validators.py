from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK"}

def validate_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s or not s.isalpha():
        raise ValueError(f"Invalid symbol '{symbol}'. Must be letters only, e.g. BTCUSDT.")
    return s

def validate_side(side: str) -> str:
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValueError(f"Invalid side '{side}'. Must be one of: {', '.join(VALID_SIDES)}.")
    return s

def validate_order_type(order_type: str) -> str:
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. Must be one of: {', '.join(VALID_ORDER_TYPES)}."
        )
    return t

def validate_quantity(quantity: str) -> Decimal:
    try:
        q = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if q <= 0:
        raise ValueError(f"Quantity must be > 0, got {q}.")
    return q

def validate_price(price: Optional[str]) -> Optional[Decimal]:
    if price is None:
        return None
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be > 0, got {p}.")
    return p

def validate_stop_price(stop_price: Optional[str]) -> Optional[Decimal]:
    if stop_price is None:
        return None
    try:
        p = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Invalid stop price '{stop_price}'.")
    if p <= 0:
        raise ValueError(f"Stop price must be > 0.")
    return p

def validate_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
) -> dict:
    """
    Validate all fields together and return a clean dict ready for API use.
    Raises ValueError with a clear message on any issue.
    """
    result = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
    }

    if result["type"] == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders.")
        result["price"] = validate_price(price)
        result["timeInForce"] = "GTC"

    if result["type"] == "STOP_MARKET":
        if stop_price is None:
            raise ValueError("Stop price is required for STOP_MARKET orders.")
        result["stopPrice"] = validate_stop_price(stop_price)
        result["workingType"] = "MARK_PRICE"
        result["reduceOnly"] = "true" 

    return result
