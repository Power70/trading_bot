from __future__ import annotations

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
    side_color = "green" if params["side"] == "BUY" else "red"
    table.add_row("Side", f"[{side_color}]{params['side']}[/{side_color}]")
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
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET or LIMIT (or STOP_MARKET)"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Order quantity"),
    price: Optional[float] = typer.Option(
        None, "--price", "-p", help="Limit price (required for LIMIT orders)"
    ),
    stop_price: Optional[float] = typer.Option(
        None, "--stop-price", help="Stop trigger price (for STOP_MARKET orders)"
    ),
):
    """Place a MARKET or LIMIT order on Binance Futures Testnet."""

    # Set price to stop_price if STOP_MARKET and price not provided
    if order_type.upper() == "STOP_MARKET" and stop_price is not None and price is None:
        price = stop_price

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
    console.print(
        Panel("[bold green]✓ Order placed successfully![/bold green]", border_style="green")
    )
    _print_order_response(response)


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
    elif order_type.upper() == "STOP_MARKET":
        price = typer.prompt("Stop price", type=float)
    
    # Hand off to the regular flow
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

    _print_request_summary(params)

    confirmed = typer.confirm("Proceed with this order?", default=True)
    if not confirmed:
        console.print("[yellow]Order cancelled by user.[/yellow]")
        raise typer.Exit(code=0)

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

    console.print(
        Panel("[bold green]✓ Order placed successfully![/bold green]", border_style="green")
    )
    _print_order_response(response)


if __name__ == "__main__":
    app()
