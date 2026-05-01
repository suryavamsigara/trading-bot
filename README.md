# Binance Futures Testnet Trading Bot

A Python trading bot for Binance USDT-M Futures Testnet.  
Two modes: **interactive menu** with live price context, or **single-shot CLI flags**.

---

## Project Structure

```
trading_bot/
├── agent/
│   ├── __init__.py
│   ├── client.py          # HTTP client - signing, requests, error handling
│   ├── orders.py          # Order placement logic, returns typed OrderResult
│   ├── validators.py      # Input validation, fails fast with clear messages
│   └── logging_config.py  # Dual-channel: JSON-lines file + coloured console
├── cli.py                 # CLI entry point (interactive + single-shot)
├── logs/                  # Auto-created on first run
├── pyproject.toml
└── README.md
```

---

## Setup

### 1. Get Testnet credentials

1. Visit [Binance Futures Testnet](https://testnet.binancefuture.com)
2. Register / log in -> **API Management** -> generate a key pair

### 2. Clone the repo

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone
git clone https://github.com/suryavamsigara/trading-bot.git

# uv sync
uv sync
```

Activate the venv:
```bash
# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Set credentials

```bash
export BINANCE_API_KEY="your_key_here"
export BINANCE_API_SECRET="your_secret_here"
```

Or pass inline with `--api-key` / `--api-secret` or save in .env file

---

## Usage

### Interactive mode

```bash
uv run python cli.py
```


### Single-shot mode

```bash
# Market order
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# Limit order
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --qty 0.01 --price 3200

# Stop-Market order
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop-price 75000
```

### All flags

| Flag | Description |
|------|-------------|
| `--symbol` | Trading pair, e.g. `BTCUSDT` |
| `--side` | `BUY` or `SELL` |
| `--type` | `MARKET`, `LIMIT`, or `STOP_MARKET` |
| `--qty` | Order quantity |
| `--price` | Limit price (required for `LIMIT`) |
| `--stop-price` | Stop trigger price (required for `STOP_MARKET`) |
| `--api-key` | API key (or `BINANCE_API_KEY` env var) |
| `--api-secret` | API secret (or `BINANCE_API_SECRET` env var) |
| `--verbose` / `-v` | Show DEBUG logs in the terminal too |
| `--log-file` | Custom log filename (default: `trading_bot.log`) |

---

## Logging

Each run appends to `logs/<log-file>` in JSON-lines format — one object per line.

```json
{"ts": "2026-05-01T16:58:47.820705+00:00", "level": "INFO", "logger": "trading_bot.orders", "msg": "Placing BUY STOP_MARKET order | symbol=BTCUSDT qty=0.001 price=MARKET algo=True"}
```

Filter errors with `jq`:
```bash
cat logs/trading_bot.log | jq 'select(.level == "ERROR")'
```

---
