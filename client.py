import hmac
import hashlib
import time
import requests
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlencode

TESTNET_BASE = "https://testnet.binancefuture.com"

@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    raw: dict = field(default_factory=dict)

class BinanceClient:
    """Handles auth, validation, and order placement"""
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.session= requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})
    
    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params)
        sig = hmac.new(self.api_secret, query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params
    
    def get_price(self, symbol: str) -> float:
        resp = self.session.get(f"{TESTNET_BASE}/fapi/v1/ticker/price", params={"symbol": symbol.upper()})
        resp.raise_for_status()
        return float(resp.json()["price"])
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: str, price: str = None, stop_price: str = None) -> OrderResult:
        # Validation
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity)
        }

        if params["type"] == "LIMIT":
            if not price:
                return OrderResult(success=False, error="Price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = "GTC"

        if params["type"] == "STOP_MARKET":
            if not stop_price:
                return OrderResult(success=False, error="Stop price is required for STOP_MARKET.")
            params["stopPrice"] = str(stop_price)
        
        try:
            resp = self.session.post(f"{TESTNET_BASE}/fapi/v1/order", params=self._sign(params))
            data = resp.json()

            if resp.status_code != 200:
                return OrderResult(success=False, error=data.get("msg", "Unknown API Error"), raw=data)
            
            return OrderResult(
                success=True,
                order_id=data.get("orderId"),
                symbol=data.get("symbol"),
                side=data.get("side"),
                order_type=data.get("type"),
                status=data.get("status"),
                raw=data
            )
        except Exception as e:
            return OrderResult(success=False, error=f"Network or execution error: {str(e)}")