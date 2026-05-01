import os
import sys
import argparse
from dotenv import load_dotenv
from client import BinanceClient, OrderResult

load_dotenv()

R = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
GREEN = "\x1b[38;5;84m"
RED = "\x1b[38;5;203m"
YELLOW = "\x1b[38;5;220m"
CYAN = "\x1b[38;5;87m"
MAGENTA = "\x1b[38;5;177m"
WHITE = "\x1b[38;5;255m"
GREY = "\x1b[38;5;245m"

BUY_COL = GREEN
SELL_COL = RED

def _c(text, *codes) -> str:
    return "".join(codes) + str(text) + R

def banner() -> None:
    print(f"""
{_c('╔══════════════════════════════════════════════╗', BOLD, CYAN)}
{_c('║', BOLD, CYAN)}   {_c('  Binance Futures Testnet Trading Bot', BOLD, WHITE)}      {_c('║', BOLD, CYAN)}
{_c('╚══════════════════════════════════════════════╝', BOLD, CYAN)}
""")

def _separator() -> None:
    print(_c("─" * 48, DIM, GREY))

def _prompt(label: str, hint: str = "", default: str = "") -> str:
    hint_str = f" {_c('(' + hint + ')', DIM, GREY)}" if hint else ""
    default_str = f" {_c('[' + default + ']', DIM, CYAN)}" if default else ""
    raw = input(f"  {_c('▸', BOLD, CYAN)} {_c(label, WHITE)}{hint_str}{default_str}: ").strip()
    return raw if raw else default

def _ask_choice(label: str, choices: list[str]) -> str:
    print(f"\n  {_c(label, BOLD, WHITE)}")
    for i, c in enumerate(choices, 1):
        print(f"    {_c(str(i) + '.', CYAN)} {c}")
    while True:
        raw = input(f"  {_c('▸', BOLD, CYAN)} Choice: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        print(f"  {_c('! Enter a number 1–' + str(len(choices)), YELLOW)}")

def print_result(result: OrderResult) -> None:
    if not result.success:
        print(f"\n  {_c('✗ ORDER FAILED', BOLD, RED)}")
        print(f"  {_c(result.error, RED)}\n")
        return

    side_col = BUY_COL if result.side == "BUY" else SELL_COL
    print(f"\n  {_c('✓ ORDER PLACED', BOLD, GREEN)}\n")
    print(f"  {'Order ID':<18} {_c(result.order_id, BOLD, WHITE)}")
    print(f"  {'Symbol':<18} {_c(result.symbol, WHITE)}")
    print(f"  {'Side':<18} {_c(result.side, BOLD, side_col)}")
    print(f"  {'Type':<18} {_c(result.order_type, MAGENTA)}")
    print(f"  {'Status':<18} {_c(result.status, BOLD, GREEN)}")
    _separator()

def run_interactive(client: BinanceClient) -> None:
    banner()
    while True:
        print(f"\n  {_c('What would you like to do?', BOLD, WHITE)}")
        action = _ask_choice("", ["Place a new order", "Check live price", "Exit"])

        if action == "Exit":
            print(f"\n  {_c('Goodbye..', DIM, GREY)}\n")
            break

        if action == "Check live price":
            sym = _prompt("Symbol", "e.g. BTCUSDT", "BTCUSDT").upper()
            try:
                p = client.get_price(sym)
                print(f"\n  {_c(sym, BOLD, WHITE)}  →  {_c(f'${p:,.4f}', BOLD, GREEN)}\n")
            except Exception as exc:
                print(f"\n  {_c('Error: ' + str(exc), RED)}\n")
            continue

        print(f"\n  {_c('NEW ORDER', BOLD, CYAN)}\n")
        symbol = _prompt("Symbol", "e.g. BTCUSDT", "BTCUSDT").upper()
        side = _ask_choice("Side", ["BUY", "SELL"])
        order_type = _ask_choice("Order type", ["MARKET", "LIMIT", "STOP_MARKET"])
        quantity = _prompt("Quantity", "e.g. 0.001")

        price = _prompt("Limit price", "e.g. 29000") if order_type == "LIMIT" else None
        stop_price = _prompt("Stop trigger price", "e.g. 28000") if order_type == "STOP_MARKET" else None

        confirm = input(f"  {_c('▸', BOLD, CYAN)} {_c('Confirm Order? [y/N]: ', WHITE)}").strip().lower()
        if confirm != "y":
            print(f"\n  {_c('Order cancelled.', YELLOW)}\n")
            continue

        result = client.place_order(symbol, side, order_type, quantity, price, stop_price)
        print_result(result)

def main():
    parser = argparse.ArgumentParser(prog="trading_bot")
    parser.add_argument("--symbol", help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", choices=["BUY", "SELL"])
    parser.add_argument("--type", choices=["MARKET", "LIMIT", "STOP_MARKET"])
    parser.add_argument("--qty", help="Order quantity")
    parser.add_argument("--price", default=None, help="Limit price")
    parser.add_argument("--stop-price", dest="stop_price", default=None)
    args = parser.parse_args()

    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        print(f"\n  {_c('Error:', BOLD, RED)} API credentials not set (BINANCE_API_KEY / BINANCE_API_SECRET).\n")
        sys.exit(1)

    client = BinanceClient(api_key, api_secret)

    if args.symbol and args.side and args.type and args.qty:
        result = client.place_order(args.symbol, args.side, args.type, args.qty, args.price, args.stop_price)
        print_result(result)
        sys.exit(0 if result.success else 1)
    else:
        run_interactive(client)

if __name__ == "__main__":
    main()