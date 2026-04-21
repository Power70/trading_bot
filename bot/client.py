from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.parse

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
        self.api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY")
        self.secret_key = secret_key or os.environ.get("BINANCE_TESTNET_SECRET_KEY")
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

        safe_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("GET %s | params=%s", endpoint, safe_params)

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
