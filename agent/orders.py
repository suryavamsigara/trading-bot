from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

from agent.client import BinanceClient, BinanceAPIError
from agent.validators import validate_order_request

logger = logging.getLogger("trading_bot.orders")

ALGO_ORDER_TYPES = {"STOP_MARKET", "TAKE_PROFIT_MARKET", "STOP", "TAKE_PROFIT", "TRAILING_STOP_MARKET"}


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    trigger_price: Optional[str] = None
    time_in_force: Optional[str] = None
    is_algo: bool = False
    raw: dict = field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: dict, is_algo: bool = False) -> "OrderResult":
        if is_algo:
            return cls(
                success=True,
                is_algo=True,
                order_id=data.get("algoId"),
                symbol=data.get("symbol"),
                side=data.get("side"),
                order_type=data.get("orderType"),
                status=data.get("algoStatus"),
                orig_qty=data.get("quantity"),
                executed_qty=None,
                avg_price=None,
                price=data.get("price"),
                trigger_price=data.get("triggerPrice"),
                time_in_force=data.get("timeInForce"),
                raw=data,
            )
        return cls(
            success=True,
            is_algo=False,
            order_id=data.get("orderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("type"),
            status=data.get("status"),
            orig_qty=data.get("origQty"),
            executed_qty=data.get("executedQty"),
            avg_price=data.get("avgPrice") or data.get("price"),
            price=data.get("price"),
            trigger_price=data.get("stopPrice"),
            time_in_force=data.get("timeInForce"),
            raw=data,
        )

    @classmethod
    def from_error(cls, error: str) -> "OrderResult":
        return cls(success=False, error=error)


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
) -> OrderResult:
    """
    Validate inputs, route to the correct endpoint, and place the order.
    Returns an OrderResult regardless of outcome — never raises.
    """
    # 1. Validate
    try:
        params = validate_order_request(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as exc:
        logger.warning("Validation failed: %s", exc)
        return OrderResult.from_error(str(exc))

    order_type_upper = params["type"]
    is_algo = order_type_upper in ALGO_ORDER_TYPES

    logger.info(
        "Placing %s %s order | symbol=%s qty=%s price=%s algo=%s",
        params["side"],
        order_type_upper,
        params["symbol"],
        params["quantity"],
        params.get("price", "MARKET"),
        is_algo,
    )

    # 2. Route and build payload
    try:
        if is_algo:
            response = _place_algo(client, params)
        else:
            response = _place_standard(client, params)

        result = OrderResult.from_api_response(response, is_algo=is_algo)
        logger.info(
            "Order placed | id=%s status=%s executedQty=%s",
            result.order_id,
            result.status,
            result.executed_qty,
        )
        return result

    except BinanceAPIError as exc:
        logger.error("API error placing order: %s", exc)
        return OrderResult.from_error(str(exc))
    except ConnectionError as exc:
        logger.error("Network error placing order: %s", exc)
        return OrderResult.from_error(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error placing order")
        return OrderResult.from_error(f"Unexpected error: {exc}")

def _place_standard(client: BinanceClient, params: dict) -> dict:
    api_params = {
        "symbol": params["symbol"],
        "side": params["side"],
        "type": params["type"],
        "quantity": str(params["quantity"]),
    }
    if "price" in params:
        api_params["price"] = str(params["price"])
    if "timeInForce" in params:
        api_params["timeInForce"] = params["timeInForce"]
    return client.place_order(**api_params)


def _place_algo(client: BinanceClient, params: dict) -> dict:
    api_params = {
        "symbol": params["symbol"],
        "side": params["side"],
        "algoType": "CONDITIONAL",
        "type": params["type"],
        "quantity": str(params["quantity"]),
        "workingType": "MARK_PRICE",
        "reduceOnly": "true", 
    }
    if "stopPrice" in params:
        api_params["triggerPrice"] = str(params["stopPrice"]) 
    if "price" in params:
        api_params["price"] = str(params["price"])
    if "timeInForce" in params:
        api_params["timeInForce"] = params["timeInForce"]

    return client.place_algo_order(**api_params)
