import hmac
import hashlib
import time
import httpx
import logging
from typing import Any
from urllib.parse import urlencode

TESTNET_BASE = "https://testnet.binancefuture.com"

logger = logging.getLogger("trading_bot.client")

class BinanceAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")

class BinanceClient:
    """Handles auth, validation, and order placement"""
    def __init__(self, api_key: str, api_secret: str, timeout: float=10.0):
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.base = TESTNET_BASE
        self._client = httpx.Client(
            base_url=self.base,
            headers={
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=timeout,
        )
        logger.debug("BinanceClient initialised — base=%s", self.base)
    
    def _sign(self, params: dict) -> dict:
        """Append recvWindow + timestamp and HMAC-SHA256 signature."""
        params["recvWindow"] = 5000
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params)
        sig = hmac.new(self.api_secret, query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params
    
    def _request(self, method: str, path: str, signed: bool, **kwargs) -> Any:
        params = kwargs.pop("params", {})
        if signed:
            params = self._sign(params)

        logger.info("→ %s %s | params=%s", method.upper(), path, params)
        try:
            if method.upper() == "POST":
                resp = self._client.request(method, path, data=params, **kwargs) # Use 'data'
            else:
                resp = self._client.request(method, path, params=params, **kwargs) 
        except httpx.TimeoutException as exc:
            logger.error("Network timeout: %s", exc)
            raise ConnectionError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            logger.error("Network error: %s", exc)
            raise ConnectionError(f"Network failure: {exc}") from exc

        logger.info("← %s %s", resp.status_code, resp.text[:400])

        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            return {}

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(data["code"], data.get("msg", "unknown"))

        resp.raise_for_status()
        return data
    
    def get_exchange_info(self) -> dict:
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_price(self, symbol: str) -> float:
        data = self._request(
            "GET", "/fapi/v1/ticker/price", signed=False, params={"symbol": symbol}
        )
        return float(data["price"])

    def get_account(self) -> dict:
        return self._request("GET", "/fapi/v2/account", signed=True, params={})

    def place_order(self, **order_params) -> dict:
        return self._request(
            "POST", "/fapi/v1/order", signed=True, params=order_params
        )
    
    def place_algo_order(self, **order_params) -> dict:
        return self._request(
            "POST", "/fapi/v1/algoOrder", signed=True, params=order_params
        )

    def get_order(self, symbol: str, order_id: int) -> dict:
        return self._request(
            "GET",
            "/fapi/v1/order",
            signed=True,
            params={"symbol": symbol, "orderId": order_id},
        )

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            signed=True,
            params={"symbol": symbol, "orderId": order_id},
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
