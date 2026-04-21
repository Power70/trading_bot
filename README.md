# Binance Futures Testnet Trading Bot

A CLI trading bot for placing MARKET and LIMIT orders on Binance Futures Testnet (USDT-M).

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed
- A Binance Futures Testnet account with API credentials

## Setup

### 1. Clone the repository

git clone <your-repo-url>
cd trading_bot

### 2. Install dependencies

uv sync

### 3. Configure credentials

cp .env.example .env
# Edit .env and fill in your API key and secret

### 4. Activate the virtual environment

source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

## Usage

### Place a MARKET order

uv run python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

### Place a LIMIT order

uv run python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 95000

### Get help

uv run python cli.py order --help

### Using the installed script (after uv sync)

trade order --symbol ETHUSDT --side BUY --type MARKET --quantity 0.1

## Examples

#### Buy 0.01 BTC at market price
uv run python cli.py order -s BTCUSDT --side BUY -t MARKET -q 0.01

#### Buy 0.04 BTC at market price
uv run python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.04

#### Sell 0.01 BTC with a limit at $95,000
uv run python cli.py order -s BTCUSDT --side SELL -t LIMIT -q 0.01 -p 95000

#### Place a Stop-Market order (Bonus)
uv run python cli.py order -s BTCUSDT --side SELL -t STOP_MARKET -q 0.01 --stop-price 90000

#### Launch Interactive Mode (Bonus)
uv run python cli.py interactive

## Logs

All API activity is logged to `logs/trading_bot.log`. This includes:
- Full request parameters (excluding signature)
- Full response bodies
- All errors with stack traces

## Assumptions

- The Binance Futures Testnet API is used exclusively (no real funds)
- Quantity precision must match the symbol's LOT_SIZE filter (e.g., 0.001 for BTCUSDT)
- LIMIT orders use GTC (Good Till Cancelled) time-in-force by default
- The user has already funded their testnet account via the testnet faucet

## Project Structure

trading_bot/
├── bot/
│   ├── client.py          # HTTP client with HMAC signing
│   ├── orders.py          # Order placement logic
│   ├── validators.py      # Input validation
│   └── logging_config.py  # Rotating file + console logging
├── cli.py                 # CLI entry point (Typer + Rich)
├── logs/                  # Generated at runtime
├── .env.example           # Credential template
├── pyproject.toml         # Dependencies
└── README.md
