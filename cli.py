import os
import sys
import time
import hmac
import hashlib
import argparse
import requests
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

BASE_URL = "https://testnet.binancefuture.com"

class BinanceClient:    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key
        })

    def _sign(self, params: dict) -> dict:
        """Adds a timestamp and HMAC-SHA256 signature to the payload."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(self.api_secret, query_string.encode(), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params

    def get_price(self, symbol: str) -> float:
        """Fetches the current price of a symbol."""
        url = f"{BASE_URL}/fapi/v1/ticker/price"
        response = self.session.get(url, params={"symbol": symbol.upper()})
        response.raise_for_status()
        return float(response.json()["price"])

    def place_order(self, symbol: str, side: str, order_type: str, quantity: str, price: str = None) -> dict:
        """Places a MARKET or LIMIT order."""
        url = f"{BASE_URL}/fapi/v1/order"
        
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
        }
        
        if order_type.upper() == "LIMIT":
            if not price:
                raise ValueError("Price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = "GTC"
            
        if order_type.upper() == "STOP_MARKET":
            if not price:
                raise ValueError("Stop price is required for STOP_MARKET orders.")
            params["stopPrice"] = str(price)

        signed_params = self._sign(params)
        response = self.session.post(url, data=signed_params)

        if response.status_code != 200:
            print(f"\n[X] Order Failed: {response.text}")
            return {}
            
        return response.json()

def run_interactive(client: BinanceClient):
    print("\n=== Binance Futures Testnet Bot ===")
    
    while True:
        print("\nOptions: [1] Place Order  [2] Check Price  [3] Exit")
        action = input("Choose an option (1/2/3): ").strip()
        
        if action == "3":
            print("Exiting..")
            break
            
        elif action == "2":
            sym = input("Symbol (e.g. BTCUSDT): ").strip().upper() or "BTCUSDT"
            try:
                price = client.get_price(sym)
                print(f"  {sym} Live Price: ${price:,.4f}")
            except Exception as e:
                print(f"  [!] Error fetching price: {e}")
                
        elif action == "1":
            symbol = input("Symbol (e.g. BTCUSDT): ").strip().upper()
            side = input("Side (BUY/SELL): ").strip().upper()
            order_type = input("Type (MARKET/LIMIT/STOP_MARKET): ").strip().upper()
            qty = input("Quantity (e.g. 0.001): ").strip()

            price = None
            if order_type in ["LIMIT", "STOP_MARKET"]:
                price = input("Price (Limit or Stop): ").strip()

            print(f"\nPlacing {side} {qty} {symbol} ({order_type})...")
            try:
                result = client.place_order(symbol, side, order_type, qty, price)
                if result:
                    print(f"\nOrder Success!")
                    print(f"    ID:     {result.get('orderId')}")
                    print(f"    Status: {result.get('status')}")
            except Exception as e:
                print(f"  [!] Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Binance Testnet Bot")
    parser.add_argument("--symbol", help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", choices=["BUY", "SELL"])
    parser.add_argument("--type", choices=["MARKET", "LIMIT", "STOP_MARKET"])
    parser.add_argument("--qty", help="Order quantity")
    parser.add_argument("--price", help="Price for LIMIT or STOP_MARKET orders")
    args = parser.parse_args()

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print("Error: BINANCE_API_KEY and BINANCE_API_SECRET environment variables must be set.")
        sys.exit(1)

    client = BinanceClient(api_key, api_secret)

    if args.symbol and args.side and args.type and args.qty:
        try:
            result = client.place_order(args.symbol, args.side, args.type, args.qty, args.price)
            if result:
                print(f"Order Placed! ID: {result.get('orderId')} | Status: {result.get('status')}")
        except Exception as e:
            print(f"[!] Error: {e}")
            sys.exit(1)
    else:
        run_interactive(client)

if __name__ == "__main__":
    main()