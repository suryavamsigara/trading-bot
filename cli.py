"""
CLI entry point - two modes:

  1. Interactive menu (default): guided UX with live price fetch.
  2. Single-shot flags:  trade --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

Run:  python cli.py [flags]   or just   python cli.py
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from typing import Optional
from dotenv import load_dotenv

from agent.client import BinanceClient, BinanceAPIError
from agent.logging_config import setup_logging
from agent.orders import place_order, OrderResult

load_dotenv()


R = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
GREEN = "\x1b[38;5;84m"
RED = "\x1b[38;5;203m"
YELLOW = "\x1b[38;5;220m"
CYAN = "\x1b[38;5;87m"
BLUE = "\x1b[38;5;75m"
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


def print_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str],
    stop_price: Optional[str],
    live_price: Optional[float],
) -> None:
    side_col = BUY_COL if side == "BUY" else SELL_COL
    _separator()
    print(f"\n  {_c('ORDER SUMMARY', BOLD, WHITE)}\n")
    print(f"  {'Symbol':<16} {_c(symbol, BOLD, WHITE)}")
    print(f"  {'Side':<16} {_c(side, BOLD, side_col)}")
    print(f"  {'Type':<16} {_c(order_type, BOLD, MAGENTA)}")
    print(f"  {'Quantity':<16} {_c(quantity, WHITE)}")
    if price:
        print(f"  {'Limit Price':<16} {_c(price, WHITE)}")
    if stop_price:
        print(f"  {'Stop Price':<16} {_c(stop_price, YELLOW)}")
    if live_price:
        print(f"  {'Live Price':<16} {_c(f'${live_price:,.4f}', DIM, GREY)}")
    _separator()

def print_result(result: OrderResult) -> None:
    if not result.success:
        print(f"\n  {_c('✗ ORDER FAILED', BOLD, RED)}")
        print(f"  {_c(result.error, RED)}\n")
        return

    side_col = BUY_COL if result.side == "BUY" else SELL_COL
    status_col = GREEN if result.status in ("FILLED", "NEW") else YELLOW

    print(f"\n  {_c('✓ ORDER PLACED', BOLD, GREEN)}\n")
    print(f"  {'Order ID':<18} {_c(result.order_id, BOLD, WHITE)}")
    print(f"  {'Symbol':<18} {_c(result.symbol, WHITE)}")
    print(f"  {'Side':<18} {_c(result.side, BOLD, side_col)}")
    print(f"  {'Type':<18} {_c(result.order_type, MAGENTA)}")
    print(f"  {'Status':<18} {_c(result.status, BOLD, status_col)}")
    print(f"  {'Orig Qty':<18} {_c(result.orig_qty, WHITE)}")
    print(f"  {'Executed Qty':<18} {_c(result.executed_qty, WHITE)}")

    avg = result.avg_price
    if avg and float(avg) > 0:
        print(f"  {'Avg Price':<18} {_c('$' + avg, GREEN)}")

    if result.time_in_force:
        print(f"  {'Time In Force':<18} {_c(result.time_in_force, GREY)}")
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

        live_price = None
        try:
            live_price = client.get_price(symbol)
            print(f"  {_c('Live price:', DIM, GREY)} {_c(f'${live_price:,.4f}', GREEN)}")
        except Exception:
            pass

        side = _ask_choice("Side", ["BUY", "SELL"])
        order_type = _ask_choice("Order type", ["MARKET", "LIMIT", "STOP_MARKET"])
        quantity = _prompt("Quantity", "e.g. 0.001")

        price = None
        stop_price = None

        if order_type == "LIMIT":
            price = _prompt("Limit price", "e.g. 29000")

        if order_type == "STOP_MARKET":
            stop_price = _prompt("Stop trigger price", "e.g. 28000")

        print_summary(symbol, side, order_type, quantity, price, stop_price, live_price)

        confirm = input(f"  {_c('▸', BOLD, CYAN)} {_c('Confirm? [y/N]: ', WHITE)}").strip().lower()
        if confirm != "y":
            print(f"\n  {_c('Order cancelled.', YELLOW)}\n")
            continue

        result = place_order(
            client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
        print_result(result)

        again = input(f"  {_c('Place another order? [y/N]: ', DIM, GREY)}").strip().lower()
        if again != "y":
            print(f"\n  {_c('Session ended.', DIM, GREY)}\n")
            break

def run_single_shot(args: argparse.Namespace, client: BinanceClient) -> None:
    banner()

    live_price = None
    try:
        live_price = client.get_price(args.symbol.upper())
    except Exception:
        pass

    print_summary(
        symbol=args.symbol.upper(),
        side=args.side.upper(),
        order_type=args.type.upper(),
        quantity=args.qty,
        price=args.price,
        stop_price=args.stop_price,
        live_price=live_price,
    )

    result = place_order(
        client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.qty,
        price=args.price,
        stop_price=args.stop_price,
    )
    print_result(result)
    sys.exit(0 if result.success else 1)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet trading bot",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cli.py                                           # interactive menu\n"
            "  python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001\n"
            "  python cli.py --symbol ETHUSDT --side SELL --type LIMIT --qty 0.01 --price 3000\n"
            "  python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop-price 28000\n"
        ),
    )
    parser.add_argument("--symbol", help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument("--type", choices=["MARKET", "LIMIT", "STOP_MARKET", "market", "limit", "stop_market"])
    parser.add_argument("--qty", help="Order quantity")
    parser.add_argument("--price", default=None, help="Limit price (required for LIMIT orders)")
    parser.add_argument("--stop-price", dest="stop_price", default=None, help="Stop trigger price (STOP_MARKET)")
    parser.add_argument("--api-key", default=None, help="Binance API key (or set BINANCE_API_KEY env var)")
    parser.add_argument("--api-secret", default=None, help="Binance API secret (or set BINANCE_API_SECRET env var)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show DEBUG logs on console too")
    parser.add_argument("--log-file", default="trading_bot.log", help="Log file name (default: trading_bot.log)")
    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(log_file=args.log_file, verbose=args.verbose)

    api_key = args.api_key or os.getenv("BINANCE_API_KEY", "")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        print(
            f"\n  {_c('Error:', BOLD, RED)} API credentials not set.\n"
            f"  Export {_c('BINANCE_API_KEY', CYAN)} and {_c('BINANCE_API_SECRET', CYAN)}, "
            f"or pass {_c('--api-key / --api-secret', CYAN)}.\n"
        )
        sys.exit(1)

    # Determine mode
    single_shot_args = [args.symbol, args.side, args.type, args.qty]
    is_single_shot = all(x is not None for x in single_shot_args)

    with BinanceClient(api_key, api_secret) as client:
        if is_single_shot:
            run_single_shot(args, client)
        elif any(x is not None for x in single_shot_args):
            parser.error(
                "For single-shot mode, supply all of: --symbol --side --type --qty"
            )
        else:
            run_interactive(client)

if __name__ == "__main__":
    main()