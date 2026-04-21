# Implementation Plan: Binance Futures Testnet Trading Bot
## Python Developer Intern Assignment — Primetrade.ai

---

## Table of Contents

1. [Overview & Architecture Philosophy](#1-overview--architecture-philosophy)
2. [What You Need Before Writing a Single Line of Code](#2-what-you-need-before-writing-a-single-line-of-code)
3. [Project Structure](#3-project-structure)
4. [Environment Setup with uv](#4-environment-setup-with-uv)
5. [Dependencies & pyproject.toml](#5-dependencies--pyprojecttoml)
6. [Binance Testnet Account Setup](#6-binance-testnet-account-setup)
7. [Module-by-Module Implementation](#7-module-by-module-implementation)
   - 7.1 [logging_config.py](#71-logging_configpy)
   - 7.2 [validators.py](#72-validatorspy)
   - 7.3 [client.py](#73-clientpy)
   - 7.4 [orders.py](#74-orderspy)
   - 7.5 [cli.py](#75-clipy)
   - 7.6 [__init__.py files](#76-__init__py-files)
8. [Configuration & Secrets Management](#8-configuration--secrets-management)
9. [README.md Specification](#9-readmemd-specification)
10. [Testing & Validation Checklist](#10-testing--validation-checklist)
11. [Generating Required Log Files](#11-generating-required-log-files)
12. [Bonus Features Implementation](#12-bonus-features-implementation)
13. [GitHub Repository Setup](#13-github-repository-setup)
14. [Evaluation Criteria Self-Audit](#14-evaluation-criteria-self-audit)
15. [Common Pitfalls & How to Avoid Them](#15-common-pitfalls--how-to-avoid-them)

---

## 1. Overview & Architecture Philosophy

### What This App Is
A production-quality CLI trading bot that places MARKET and LIMIT orders on Binance Futures Testnet (USDT-M). It is designed with three hard principles:

- **Separation of concerns**: The API/network layer never touches the CLI. The CLI never does business logic.
- **Fail loudly but gracefully**: Every error is caught, logged with full context, and communicated to the user in plain English.
- **Zero magic**: No globals, no hidden state. Every function accepts what it needs as explicit parameters.

### Layered Architecture

```
User (CLI input)
      │
      ▼
cli.py           ← parses args, formats output, calls orders layer
      │
      ▼
validators.py    ← validates all input BEFORE any network call
      │
      ▼
orders.py        ← composes order payloads, calls client layer
      │
      ▼
client.py        ← handles HTTP, auth (HMAC-SHA256 signing), retries
      │
      ▼
Binance Futures Testnet REST API
```

Logging is a cross-cutting concern: every layer writes to the same rotating log file via a shared logger instance from `logging_config.py`.

---

## 2. What You Need Before Writing a Single Line of Code

### Knowledge Prerequisites
- **HMAC-SHA256 request signing**: Binance requires every authenticated endpoint to be signed. The signature is `hmac.new(secret_key, query_string, hashlib.sha256).hexdigest()`. You must append `timestamp` and `signature` to every private request.
- **Binance Futures vs Spot**: USDT-M Futures is a completely separate API from Spot. The base URL, endpoints, and some parameter names differ. Always use `https://testnet.binancefuture.com`.
- **Testnet limitations**: The testnet resets periodically. Balances and orders from previous sessions may disappear. This is normal.
- **REST endpoint for placing orders**: `POST /fapi/v1/order`
- **Required parameters for MARKET order**: `symbol`, `side`, `type`, `quantity`, `timestamp`, `signature`
- **Required parameters for LIMIT order**: all above + `price`, `timeInForce` (use `GTC` — Good Till Cancelled)
- **Quantity precision**: Every symbol has a defined step size for quantity. For BTCUSDT on testnet, quantity must be a multiple of 0.001. Violating this returns error code -1111. The `filters` endpoint (`GET /fapi/v1/exchangeInfo`) exposes this.
- **`recvWindow`**: Optional parameter (milliseconds) Binance allows for timestamp tolerance. Set to 5000 as default.

### Tools Required on Your Machine
- Python 3.11 or higher
- `uv` (the fast Python package manager — replaces pip/venv/poetry in one tool)
- `git`
- A terminal / shell
- A text editor or IDE

### Accounts & Credentials
- Binance Futures Testnet account (free — no real money)
- Testnet API Key and Secret (generated from the testnet dashboard)

---

## 3. Project Structure

Create exactly this directory tree. Every file listed here will be implemented.

```
trading_bot/
├── bot/
│   ├── __init__.py          # Exposes package version
│   ├── client.py            # BinanceFuturesClient: HTTP, signing, error handling
│   ├── orders.py            # place_order(): composes and dispatches orders
│   ├── validators.py        # validate_order_params(): all input checks
│   └── logging_config.py    # get_logger(): returns configured logger
├── logs/                    # Created at runtime — gitignored
│   └── .gitkeep
├── cli.py                   # Entry point: argparse CLI, output formatting
├── .env                     # API keys — gitignored, NEVER committed
├── .env.example             # Template with placeholder values — committed
├── .gitignore
├── pyproject.toml           # uv-managed: deps, scripts, metadata
└── README.md
```

---

## 4. Environment Setup with uv

Follow these steps in order. Do not skip any step.

### Step 1 — Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify
uv --version
```

### Step 2 — Create the project

```bash
# Navigate to wherever you keep projects
cd ~/projects

# Create the project with uv (creates pyproject.toml and .venv)
uv init trading_bot
cd trading_bot

# Create the required subdirectories
mkdir -p bot logs

# Create placeholder files so git tracks the empty dirs
touch logs/.gitkeep
touch bot/__init__.py bot/client.py bot/orders.py bot/validators.py bot/logging_config.py
touch cli.py .env .env.example README.md
```

### Step 3 — Create the virtual environment

```bash
# uv creates and manages the venv automatically
uv venv

# Activate it (macOS/Linux)
source .venv/bin/activate

# Activate it (Windows)
.venv\Scripts\activate
```

### Step 4 — Add dependencies

```bash
uv add httpx python-dotenv typer rich
uv add --dev pytest pytest-httpx ruff
```

After this, `uv.lock` and `pyproject.toml` will be fully populated. Never manually edit the lock file.

---

## 5. Dependencies & pyproject.toml

The final `pyproject.toml` should look like this (uv generates most of it; you fill in `[project.scripts]` and metadata):

```toml
[project]
name = "trading-bot"
version = "1.0.0"
description = "Binance Futures Testnet Trading Bot — Primetrade.ai Assignment"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27.0",        # Async-ready HTTP client; cleaner than requests
    "python-dotenv>=1.0.0", # Loads .env into os.environ
    "typer>=0.12.0",        # Modern CLI framework built on Click
    "rich>=13.7.0",         # Beautiful terminal output (tables, panels, colors)
]

[project.scripts]
trade = "cli:app"           # Allows running `trade` instead of `python cli.py`

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-httpx>=0.30.0", # Mocks httpx for unit tests
    "ruff>=0.4.0",          # Linter + formatter
]

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]

[tool.ruff.format]
quote-style = "double"
```

**Why `httpx` over `requests`?**
`httpx` has an identical API to `requests` but supports both sync and async. Using it now means the codebase can be upgraded to async later without rewriting the HTTP layer.

**Why `typer` over `argparse`?**
Typer uses Python type hints to define CLI arguments — zero boilerplate, automatic `--help` generation, built-in validation. It is the modern standard.

---

## 6. Binance Testnet Account Setup

### Step 1 — Register

1. Go to: `https://testnet.binancefuture.com`
2. Click **"Log In with GitHub"** (this is the only registration method for the testnet)
3. Authorize the OAuth app

### Step 2 — Generate API Credentials

1. After login, click your avatar → **"API Key"**
2. Click **"Generate Key"**
3. Copy both the **API Key** and **Secret Key** immediately — the secret is shown only once

### Step 3 — Fund Your Testnet Account

1. On the dashboard, click **"Get 10,000 USDT"** (the testnet faucet)
2. This gives you paper USDT to trade with

### Step 4 — Verify the API Works

Before writing the bot, test the API manually using curl:

```bash
# Public endpoint — no auth needed — verifies network connectivity
curl "https://testnet.binancefuture.com/fapi/v1/ping"
# Expected: {}

# Get server time
curl "https://testnet.binancefuture.com/fapi/v1/time"
# Expected: {"serverTime": 1234567890123}
```

If these fail, your network is blocking the testnet domain. Resolve this before proceeding.

### Step 5 — Create .env file

```bash
# In the project root
cat > .env << 'EOF'
BINANCE_TESTNET_API_KEY=your_actual_api_key_here
BINANCE_TESTNET_SECRET_KEY=your_actual_secret_key_here
BINANCE_TESTNET_BASE_URL=https://testnet.binancefuture.com
EOF
```

Create the `.env.example` template (safe to commit):

```bash
cat > .env.example << 'EOF'
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_SECRET_KEY=your_secret_key_here
BINANCE_TESTNET_BASE_URL=https://testnet.binancefuture.com
EOF
```

---

## 7. Module-by-Module Implementation

Implement each file in this exact order. Each module only depends on modules above it in the stack.

---

### 7.1 `bot/logging_config.py`

**Purpose**: Single source of truth for logging. Every other module calls `get_logger()` and gets back the same configured logger. Logs go to both the console (WARNING and above, human-readable) and a rotating file (DEBUG and above, structured).

```python
# bot/logging_config.py

import logging
import logging.handlers
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"
MAX_BYTES = 5 * 1024 * 1024   # 5 MB per log file
BACKUP_COUNT = 3               # Keep 3 rotated files


def get_logger(name: str = "trading_bot") -> logging.Logger:
    """
    Returns a configured logger instance.

    Idempotent: calling this multiple times with the same name returns
    the same logger without adding duplicate handlers.
    """
    logger = logging.getLogger(name)

    # Guard: do not add handlers if they already exist
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # --- File handler: DEBUG and above, structured format ---
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # --- Console handler: WARNING and above, concise format ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
```

**Key design decisions:**
- Rotating file handler prevents unbounded log file growth — important for long-running bots.
- Console shows WARNING+ only so normal runs are not noisy.
- The file shows DEBUG so you have full API request/response traces for debugging.
- The idempotent guard (`if logger.handlers`) is critical — without it, every module import adds duplicate handlers and you get duplicate log lines.

---

### 7.2 `bot/validators.py`

**Purpose**: All input validation happens here, before any network call is made. Every validation function raises a `ValueError` with a specific human-readable message. The CLI catches these and displays them cleanly.

```python
# bot/validators.py

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
```

**Key design decisions:**
- Each `validate_*` function validates exactly one thing — easy to test independently.
- `validate_order_params()` is the single entry point the CLI calls — it composes all individual validators.
- Returning a cleaned dict (not the raw input) means the rest of the code always works with normalised values.

---

### 7.3 `bot/client.py`

**Purpose**: The only module that touches the network. Handles HMAC-SHA256 request signing, `X-MBX-APIKEY` header injection, timestamp generation, HTTP error parsing, and logging of every request and response.

```python
# bot/client.py

from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.parse
from typing import Any

import httpx
from dotenv import load_dotenv

from bot.logging_config import get_logger

load_dotenv()

logger = get_logger()


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error code."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceFuturesClient:
    """
    Low-level Binance USDT-M Futures REST client.

    Responsibilities:
    - Inject API key header on every request
    - Sign private requests with HMAC-SHA256
    - Log all outgoing requests and incoming responses at DEBUG level
    - Raise BinanceAPIError for API-level errors
    - Raise httpx.HTTPError for network-level errors (caller handles these)
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 10.0,
    ):
        self.api_key = api_key or os.environ["BINANCE_TESTNET_API_KEY"]
        self.secret_key = secret_key or os.environ["BINANCE_TESTNET_SECRET_KEY"]
        self.base_url = (base_url or os.environ.get(
            "BINANCE_TESTNET_BASE_URL", "https://testnet.binancefuture.com"
        )).rstrip("/")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "API key and secret must be set via environment variables "
                "BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_SECRET_KEY."
            )

        self._http = httpx.Client(
            base_url=self.base_url,
            headers={"X-MBX-APIKEY": self.api_key},
            timeout=timeout,
        )

    def _sign(self, params: dict) -> dict:
        """
        Adds timestamp and signature to a parameters dict.

        The signature is HMAC-SHA256 of the URL-encoded query string,
        signed with the secret key.
        """
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000

        # URL-encode the params in the exact order they were added
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature
        return params

    def _handle_response(self, response: httpx.Response) -> dict:
        """
        Parses the HTTP response. Raises BinanceAPIError for API errors.
        Returns the parsed JSON dict on success.
        """
        logger.debug(
            "API response | status=%d | url=%s | body=%s",
            response.status_code,
            response.url,
            response.text[:2000],  # Truncate very large responses
        )

        try:
            data = response.json()
        except Exception:
            response.raise_for_status()
            return {}

        # Binance error responses always have a "code" field that is negative
        if isinstance(data, dict) and data.get("code", 0) < 0:
            raise BinanceAPIError(code=data["code"], message=data.get("msg", "Unknown error"))

        response.raise_for_status()
        return data

    def get(self, endpoint: str, params: dict | None = None, signed: bool = False) -> dict:
        """Performs a signed or unsigned GET request."""
        params = params or {}
        if signed:
            params = self._sign(params)

        logger.debug("GET %s | params=%s", endpoint, {k: v for k, v in params.items() if k != "signature"})

        response = self._http.get(endpoint, params=params)
        return self._handle_response(response)

    def post(self, endpoint: str, params: dict, signed: bool = True) -> dict:
        """Performs a signed POST request. All order endpoints require signing."""
        if signed:
            params = self._sign(params)

        # Log without the signature for cleaner logs
        safe_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("POST %s | params=%s", endpoint, safe_params)

        # Binance Futures expects params in the body as form data, NOT JSON
        response = self._http.post(endpoint, data=params)
        return self._handle_response(response)

    def close(self):
        """Closes the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
```

**Key design decisions:**
- Uses `httpx.Client` (not `requests.Session`) for connection pooling and future async upgrade path.
- The `_sign()` method always adds a fresh `timestamp` — never reuse a signed payload.
- The `__enter__`/`__exit__` context manager ensures the HTTP connection pool is always closed, preventing resource leaks.
- `safe_params` strips the signature from debug logs — a signed URL is essentially a credential.
- `BinanceAPIError` is a distinct exception class so callers can distinguish API errors from network errors.

---

### 7.4 `bot/orders.py`

**Purpose**: The business logic layer. Composes the correct parameter payload for each order type and calls the client. Does not know anything about the CLI.

```python
# bot/orders.py

from __future__ import annotations

from typing import Any

from bot.client import BinanceFuturesClient
from bot.logging_config import get_logger

logger = get_logger()

ORDER_ENDPOINT = "/fapi/v1/order"


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
    time_in_force: str = "GTC",
) -> dict[str, Any]:
    """
    Places an order on Binance Futures Testnet.

    Args:
        client:         Authenticated BinanceFuturesClient instance.
        symbol:         Trading pair (e.g., BTCUSDT). Already validated & uppercased.
        side:           "BUY" or "SELL". Already validated.
        order_type:     "MARKET" or "LIMIT". Already validated.
        quantity:       Order quantity. Already validated as positive float.
        price:          Required for LIMIT orders. None for MARKET.
        time_in_force:  "GTC" (default), "IOC", or "FOK". Only used for LIMIT.

    Returns:
        Parsed JSON response dict from Binance API.

    Raises:
        BinanceAPIError: For Binance-specific errors (invalid symbol, insufficient
                         balance, precision errors, etc.)
        httpx.HTTPError: For network-level failures.
    """
    params: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
    }

    if order_type == "LIMIT":
        params["price"] = price
        params["timeInForce"] = time_in_force

    logger.info(
        "Placing order | symbol=%s | side=%s | type=%s | qty=%s | price=%s",
        symbol, side, order_type, quantity, price,
    )

    response = client.post(ORDER_ENDPOINT, params=params)

    logger.info(
        "Order placed successfully | orderId=%s | status=%s | executedQty=%s",
        response.get("orderId"),
        response.get("status"),
        response.get("executedQty"),
    )

    return response


def get_open_orders(client: BinanceFuturesClient, symbol: str) -> list[dict]:
    """
    Fetches all open orders for a symbol.
    Useful for verifying LIMIT orders were placed correctly.
    """
    logger.debug("Fetching open orders for %s", symbol)
    return client.get("/fapi/v1/openOrders", params={"symbol": symbol}, signed=True)


def get_account_balance(client: BinanceFuturesClient) -> list[dict]:
    """
    Fetches the account balance.
    Useful for sanity-checking before placing orders.
    """
    logger.debug("Fetching account balance")
    return client.get("/fapi/v2/balance", signed=True)
```

**Key design decisions:**
- `place_order()` accepts already-validated, already-typed parameters — it trusts the validators layer.
- `time_in_force` defaults to `"GTC"` (Good Till Cancelled) which is the standard for LIMIT orders.
- Both INFO-level log lines bookend the API call — you can see in the log file whether the error happened before or after the request.

---

### 7.5 `bot/cli.py` (The main entry point: `cli.py` in project root)

**Purpose**: Parses CLI arguments using Typer, calls validators, instantiates the client, calls orders, and formats the output with Rich tables and panels. This layer handles all user-facing concerns.

```python
# cli.py  (in project root, not inside bot/)

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bot.client import BinanceAPIError, BinanceFuturesClient
from bot.logging_config import get_logger
from bot.orders import place_order
from bot.validators import validate_order_params

app = typer.Typer(
    name="trade",
    help="Binance Futures Testnet Trading Bot — place MARKET and LIMIT orders from your terminal.",
    add_completion=False,
)
console = Console()
logger = get_logger()


def _print_request_summary(params: dict) -> None:
    """Renders a clean table showing what is about to be sent."""
    table = Table(title="Order Request Summary", show_header=True, header_style="bold cyan")
    table.add_column("Field", style="dim")
    table.add_column("Value", style="white")

    table.add_row("Symbol", params["symbol"])
    table.add_row("Side", f"[green]{params['side']}[/green]" if params["side"] == "BUY" else f"[red]{params['side']}[/red]")
    table.add_row("Order Type", params["order_type"])
    table.add_row("Quantity", str(params["quantity"]))
    if "price" in params:
        table.add_row("Price", str(params["price"]))

    console.print(table)


def _print_order_response(response: dict) -> None:
    """Renders the key fields from the Binance order response."""
    table = Table(title="Order Response", show_header=True, header_style="bold green")
    table.add_column("Field", style="dim")
    table.add_column("Value", style="white")

    fields = [
        ("Order ID", "orderId"),
        ("Symbol", "symbol"),
        ("Status", "status"),
        ("Side", "side"),
        ("Type", "type"),
        ("Orig Qty", "origQty"),
        ("Executed Qty", "executedQty"),
        ("Avg Price", "avgPrice"),
        ("Price", "price"),
        ("Time in Force", "timeInForce"),
        ("Client Order ID", "clientOrderId"),
    ]

    for label, key in fields:
        value = response.get(key)
        if value is not None and value != "":
            table.add_row(label, str(value))

    console.print(table)


@app.command()
def order(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET or LIMIT"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Order quantity"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Limit price (required for LIMIT orders)"),
):
    """Place a MARKET or LIMIT order on Binance Futures Testnet."""

    # --- Step 1: Validate all inputs ---
    try:
        params = validate_order_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )
    except ValueError as exc:
        logger.error("Validation failed: %s", exc)
        console.print(Panel(f"[bold red]Validation Error[/bold red]\n{exc}", border_style="red"))
        raise typer.Exit(code=1)

    # --- Step 2: Show what we're about to do ---
    _print_request_summary(params)

    # --- Step 3: Confirm (optional safety check) ---
    confirmed = typer.confirm("Proceed with this order?", default=True)
    if not confirmed:
        console.print("[yellow]Order cancelled by user.[/yellow]")
        raise typer.Exit(code=0)

    # --- Step 4: Execute the order ---
    try:
        with BinanceFuturesClient() as client:
            response = place_order(
                client=client,
                symbol=params["symbol"],
                side=params["side"],
                order_type=params["order_type"],
                quantity=params["quantity"],
                price=params.get("price"),
            )

    except BinanceAPIError as exc:
        logger.error("Binance API error: code=%d message=%s", exc.code, exc.message)
        console.print(Panel(
            f"[bold red]Binance API Error[/bold red]\n"
            f"Code: {exc.code}\nMessage: {exc.message}",
            border_style="red"
        ))
        raise typer.Exit(code=1)

    except Exception as exc:
        logger.exception("Unexpected error placing order: %s", exc)
        console.print(Panel(
            f"[bold red]Unexpected Error[/bold red]\n{exc}\n\n"
            "Check logs/trading_bot.log for full details.",
            border_style="red"
        ))
        raise typer.Exit(code=1)

    # --- Step 5: Display success ---
    console.print(Panel("[bold green]✓ Order placed successfully![/bold green]", border_style="green"))
    _print_order_response(response)


if __name__ == "__main__":
    app()
```

**Key design decisions:**
- Typer's `Option(..., ...)` with `...` as default makes the argument required — Typer handles the error message automatically.
- The confirmation prompt (`typer.confirm`) is a safety net that prevents accidental orders. It defaults to `True` so pressing Enter accepts.
- `with BinanceFuturesClient() as client:` uses the context manager to guarantee the HTTP pool is always closed.
- Three distinct exception types are caught: `ValueError` (validation), `BinanceAPIError` (Binance-specific), and `Exception` (everything else including network errors).

---

### 7.6 `bot/__init__.py` files

```python
# bot/__init__.py
"""Binance Futures Testnet Trading Bot."""

__version__ = "1.0.0"
```

---

## 8. Configuration & Secrets Management

### `.gitignore` (critical — commit this before anything else)

```gitignore
# Environment secrets — NEVER commit these
.env

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# uv
.venv/
uv.lock   # Optional: some teams commit this; for a submission, committing it is fine

# Logs (keep .gitkeep, ignore actual logs)
logs/*.log
logs/*.log.*

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
```

### How secrets are loaded
`python-dotenv` is called at the top of `client.py` via `load_dotenv()`. It reads `.env` and injects values into `os.environ`. The client then reads them from `os.environ`. This means the app also works in production environments (Docker, CI/CD) where secrets are set as real environment variables — `load_dotenv()` does not override existing env vars by default.

---

## 9. README.md Specification

The README must be complete and runnable. Write it exactly as follows:

```markdown
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

python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

### Place a LIMIT order

python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 95000

### Get help

python cli.py order --help

### Using the installed script (after uv sync)

trade order --symbol ETHUSDT --side BUY --type MARKET --quantity 0.1

## Examples

#### Buy 0.01 BTC at market price
python cli.py order -s BTCUSDT --side BUY -t MARKET -q 0.01

#### Sell 0.01 BTC with a limit at $95,000
python cli.py order -s BTCUSDT --side SELL -t LIMIT -q 0.01 -p 95000

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
```

---

## 10. Testing & Validation Checklist

Run each of these commands after completing implementation. Every one must succeed.

### Environment checks
```bash
# 1. Verify uv and Python versions
uv --version          # Should be 0.4.x or higher
python --version      # Should be 3.11+

# 2. Verify all dependencies installed
uv sync
uv pip list | grep -E "httpx|typer|rich|python-dotenv"

# 3. Verify .env is populated and not committed
cat .env              # Should show your keys
git status            # .env should NOT appear in tracked files
```

### Connectivity checks
```bash
# 4. Ping the testnet
python -c "import httpx; print(httpx.get('https://testnet.binancefuture.com/fapi/v1/ping').json())"
# Expected: {}

# 5. Check server time sync
python -c "import httpx; print(httpx.get('https://testnet.binancefuture.com/fapi/v1/time').json())"
# Expected: {'serverTime': <some_ms_timestamp>}
```

### Validation layer checks
```bash
# 6. Test validation rejects bad input
python cli.py order --symbol BTCUSDT --side INVALID --type MARKET --quantity 0.01
# Expected: Validation Error panel, exit code 1

# 7. Test LIMIT order without price is rejected
python cli.py order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01
# Expected: Validation Error — price required

# 8. Test negative quantity is rejected
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity -1
# Expected: Validation Error — quantity > 0
```

### Live order checks
```bash
# 9. Place a MARKET BUY order
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
# Expected: Summary table, confirm prompt, Response table with status FILLED

# 10. Place a LIMIT SELL order
python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 99999
# Expected: Response table with status NEW (unfilled limit above market)

# 11. Verify log file was written
cat logs/trading_bot.log | head -50
# Expected: DEBUG-level entries showing POST /fapi/v1/order and response body
```

---

## 11. Generating Required Log Files

The assignment requires log files from at least one MARKET and one LIMIT order. Here is exactly how to generate them.

### Step 1 — Clear any existing log
```bash
rm -f logs/trading_bot.log
```

### Step 2 — Place a MARKET order
```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```
When prompted "Proceed with this order?" — type `y` and press Enter.

### Step 3 — Place a LIMIT order
```bash
python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 99999
```
A very high price ensures the order stays OPEN (not immediately filled) so the log clearly shows a LIMIT order being placed.

### Step 4 — Verify the log contains both orders
```bash
grep "Placing order" logs/trading_bot.log
# Should show two lines — one type=MARKET, one type=LIMIT

grep "Order placed successfully" logs/trading_bot.log
# Should show two lines
```

### Step 5 — Copy the log file for submission
```bash
cp logs/trading_bot.log logs/sample_orders.log
```

Include `logs/sample_orders.log` in your GitHub repo. The `trading_bot.log` itself is gitignored (rotating), but this named copy can be committed.

Add this to `.gitignore`:
```
logs/*.log
!logs/sample_orders.log
```

---

## 12. Bonus Features Implementation

Choose **one** from this section. All are implementable within the time budget.

### Option A — Stop-Market Order (Recommended: easiest, highest impact)

Add `"STOP_MARKET"` to `VALID_ORDER_TYPES` in `validators.py` (already done in the template above).

Add a `--stop-price` option to `cli.py`:

```python
stop_price: Optional[float] = typer.Option(None, "--stop-price", help="Stop trigger price (for STOP_MARKET orders)")
```

In `orders.py`, extend `place_order()`:
```python
if order_type == "STOP_MARKET":
    params["stopPrice"] = price  # stopPrice is the trigger price
    # quantity and side are already in params
```

### Option B — Enhanced CLI UX (interactive menu)

Add a second Typer command `interactive` that prompts the user for each field one at a time using `typer.prompt()`:

```python
@app.command()
def interactive():
    """Launch interactive order entry mode."""
    console.print(Panel("[bold cyan]Interactive Order Entry[/bold cyan]"))
    symbol = typer.prompt("Symbol (e.g. BTCUSDT)")
    side = typer.prompt("Side", default="BUY")
    order_type = typer.prompt("Order type (MARKET/LIMIT)", default="MARKET")
    quantity = typer.prompt("Quantity", type=float)
    price = None
    if order_type.upper() == "LIMIT":
        price = typer.prompt("Limit price", type=float)
    # Then call the same validation + order logic
```

---

## 13. GitHub Repository Setup

### Step 1 — Initialize git and make first commit

```bash
cd trading_bot

git init
git add .gitignore
git commit -m "chore: add gitignore"

git add pyproject.toml README.md .env.example
git commit -m "chore: project setup with uv and pyproject.toml"

git add bot/
git commit -m "feat: implement bot package (client, orders, validators, logging)"

git add cli.py
git commit -m "feat: add CLI entry point with Typer and Rich"

git add logs/sample_orders.log
git commit -m "docs: add sample log files from testnet orders"
```

### Step 2 — Create GitHub repository

1. Go to `https://github.com/new`
2. Name: `trading-bot-primetrade` (or similar)
3. Set to **Public**
4. Do NOT initialize with README (you already have one)
5. Copy the remote URL

```bash
git remote add origin https://github.com/<your-username>/trading-bot-primetrade.git
git branch -M main
git push -u origin main
```

### Step 3 — Verify the repository

Check on GitHub that:
- `.env` does NOT appear in any file listing
- `logs/sample_orders.log` IS visible
- `README.md` renders correctly
- The commit history is clean and descriptive

---

## 14. Evaluation Criteria Self-Audit

Before submitting, score yourself against each criterion:

| Criterion | How to Verify | Status |
|---|---|---|
| Places MARKET orders successfully | Check testnet dashboard + log shows `status=FILLED` | ☐ |
| Places LIMIT orders successfully | Log shows `status=NEW`, order visible on testnet | ☐ |
| Supports BUY and SELL | Test both sides for both order types | ☐ |
| CLI validates symbol | Pass `123` as symbol — should reject | ☐ |
| CLI validates side | Pass `HOLD` as side — should reject | ☐ |
| CLI validates price requirement | LIMIT without price — should reject | ☐ |
| Code separated into layers | client.py / orders.py / validators.py / cli.py | ☐ |
| Log file contains API requests | `grep "POST /fapi" logs/trading_bot.log` | ☐ |
| Log file contains responses | `grep "API response" logs/trading_bot.log` | ☐ |
| Errors are caught and handled | Pass invalid symbol to API — clean error message | ☐ |
| README has setup steps | Follow README on a fresh machine (or clean .venv) | ☐ |
| README has run examples | Copy-paste each example — all work | ☐ |
| requirements.txt / pyproject.toml present | `ls pyproject.toml` | ☐ |
| Log files from MARKET order submitted | `cat logs/sample_orders.log | grep MARKET` | ☐ |
| Log files from LIMIT order submitted | `cat logs/sample_orders.log | grep LIMIT` | ☐ |

---

## 15. Common Pitfalls & How to Avoid Them

### Pitfall 1 — Timestamp mismatch (Error -1021)
**Symptom**: `BinanceAPIError -1021: Timestamp for this request is outside of the recvWindow.`  
**Cause**: Your system clock is more than 5 seconds off from Binance's server time.  
**Fix**: Set `recvWindow=10000` in `_sign()`, or sync your system time via NTP.

### Pitfall 2 — Quantity precision (Error -1111)
**Symptom**: `BinanceAPIError -1111: Precision is over the maximum defined for this asset.`  
**Cause**: BTCUSDT requires quantity in increments of 0.001. Sending 0.0123456 fails.  
**Fix**: Round quantity to 3 decimal places before sending: `round(quantity, 3)`. For production, fetch `exchangeInfo` and use the `LOT_SIZE` filter.

### Pitfall 3 — Wrong endpoint (returns HTML 404)
**Symptom**: JSON parsing fails with a decode error.  
**Cause**: Using Spot API endpoints (`/api/v3/`) instead of Futures (`/fapi/v1/`).  
**Fix**: All endpoints must start with `/fapi/v1/` or `/fapi/v2/`.

### Pitfall 4 — Sending price for MARKET orders
**Symptom**: `BinanceAPIError -1106: Parameter 'price' sent when not required.`  
**Cause**: Including `price` in the MARKET order payload.  
**Fix**: The validators and orders layers already handle this — don't add price to the payload for MARKET orders.

### Pitfall 5 — Missing timeInForce for LIMIT orders
**Symptom**: `BinanceAPIError -1102: Mandatory parameter 'timeInForce' was not sent.`  
**Cause**: LIMIT orders on Futures require `timeInForce`.  
**Fix**: The `place_order()` function already adds `timeInForce="GTC"` for LIMIT orders — ensure this is not removed.

### Pitfall 6 — Committing .env with real credentials
**Symptom**: Exposed secrets on GitHub.  
**Fix**: Always commit `.gitignore` FIRST, before creating `.env`. Run `git status` to verify `.env` is not tracked. If accidentally committed: rotate your API keys immediately, then use `git filter-branch` or BFG Repo Cleaner to remove from history.

### Pitfall 7 — Testnet account balance reset
**Symptom**: All balances are zero; previous orders are gone.  
**Cause**: Binance periodically resets the testnet.  
**Fix**: Use the testnet faucet ("Get 10,000 USDT") button to refund your account. This is expected testnet behavior.

---

*End of Implementation Plan*

**Estimated implementation time**: 45–60 minutes for core requirements, +15 minutes for one bonus feature.  
**Submission**: Push to GitHub, submit the repository URL via the Google Form provided by the Primetrade.ai hiring team.
