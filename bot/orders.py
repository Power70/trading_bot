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
    
    # Bonus feature: STOP_MARKET
    if order_type == "STOP_MARKET":
        params["stopPrice"] = price

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
