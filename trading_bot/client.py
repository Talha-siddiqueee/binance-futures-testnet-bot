"""Minimal signed REST client for Binance USDⓈ-M Futures Demo."""

import hashlib
import hmac
import json
import logging
import re
import time
from typing import Any, Mapping
from urllib.parse import urlencode

import requests

from .exceptions import BinanceAPIError, NetworkError

LOGGER = logging.getLogger("trading_bot.api")


def _redact_signature(value: str) -> str:
    """Remove any signed query value from transport exception text."""
    return re.sub(r"([?&]signature=)[^&\s]+", r"\1[REDACTED]", value, flags=re.IGNORECASE)


class BinanceFuturesTestnetClient:
    """Small REST client pinned to the Binance USDⓈ-M Futures Demo host.

    The historical class name is retained to avoid breaking the CLI/tests.
    """

    BASE_URL = "https://demo-fapi.binance.com"
    ORDER_ENDPOINT = "/fapi/v1/order"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        timeout: float = 10.0,
        recv_window: int = 5_000,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET must be configured.")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if not 1 <= recv_window <= 60_000:
            raise ValueError("recv_window must be between 1 and 60000 ms")

        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.timeout = timeout
        self.recv_window = recv_window
        self.session = session or requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    def _signature(self, query_string: str) -> str:
        return hmac.new(
            self.api_secret, query_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
        signed: bool = False,
    ) -> dict[str, Any] | list[Any]:
        request_params = dict(params or {})
        request_params = {key: value for key, value in request_params.items() if value is not None}

        if signed:
            request_params["timestamp"] = int(time.time() * 1000)
            request_params["recvWindow"] = self.recv_window
            # Sign exactly the encoded parameter sequence sent to Binance.
            query_string = urlencode(request_params)
            request_params["signature"] = self._signature(query_string)

        url = f"{self.BASE_URL}{endpoint}"
        safe_params = {key: value for key, value in request_params.items() if key != "signature"}
        LOGGER.info(
            "API request",
            extra={"event": "api_request", "method": method.upper(), "endpoint": endpoint, "params": safe_params},
        )

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=request_params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            LOGGER.exception(
                "Network failure while calling Binance",
                extra={"event": "network_error", "method": method.upper(), "endpoint": endpoint,
                    "params": safe_params, "error": _redact_signature(str(exc))},
            )
            raise NetworkError(
                f"Could not confirm the Binance response: {_redact_signature(str(exc))}. "
                "The order outcome may be unknown; check Testnet order history before retrying.",
                outcome_unknown=True,
            ) from exc

        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            LOGGER.error(
                "Binance returned a non-JSON response",
                extra={"event": "invalid_response", "method": method.upper(), "endpoint": endpoint,
                    "http_status": response.status_code, "error": response.text[:500]},
            )
            raise NetworkError(
                f"Binance returned a non-JSON response (HTTP {response.status_code}); "
                "the order outcome may be unknown. Check Testnet order history before retrying.",
                outcome_unknown=True,
            ) from exc

        if not response.ok:
            error_code = payload.get("code") if isinstance(payload, dict) else None
            error_message = payload.get("msg", "Unknown Binance API error") if isinstance(payload, dict) else str(payload)
            LOGGER.error(
                "Binance API request failed",
                extra={"event": "api_error", "method": method.upper(), "endpoint": endpoint,
                    "params": safe_params, "http_status": response.status_code,
                    "response": payload, "error": error_message},
            )
            outcome_unknown = response.status_code >= 500
            uncertainty_note = (
                " Order execution status is UNKNOWN; check Testnet order history before retrying."
                if outcome_unknown else ""
            )
            raise BinanceAPIError(
                f"Binance API error (HTTP {response.status_code}, code {error_code}): "
                f"{error_message}.{uncertainty_note}",
                code=error_code,
                http_status=response.status_code,
                outcome_unknown=outcome_unknown,
            )

        LOGGER.info(
            "API response received",
            extra={"event": "api_response", "method": method.upper(), "endpoint": endpoint,
                "http_status": response.status_code, "response": payload},
        )
        if not isinstance(payload, (dict, list)):
            raise NetworkError("Binance returned an unexpected response format.")
        return payload

    def get_account_config(self) -> dict[str, Any]:
        """Fetch account configuration using an authenticated GET request."""
        result = self._request("GET", "/fapi/v1/accountConfig", signed=True)
        if not isinstance(result, dict):
            raise NetworkError("Unexpected account configuration response: expected a JSON object.")
        return result

    def get_exchange_info(self) -> dict[str, Any]:
        """Fetch public USDⓈ-M Futures exchange information."""
        result = self._request("GET", "/fapi/v1/exchangeInfo")
        if not isinstance(result, dict):
            raise NetworkError("Unexpected exchange information response: expected a JSON object.")
        return result

    def place_order(self, order: Mapping[str, str]) -> dict[str, Any]:
        """Submit a MARKET or LIMIT order to Binance Futures Demo."""
        params: dict[str, Any] = {
            "symbol": order["symbol"],
            "side": order["side"],
            "type": order["type"],
            "quantity": order["quantity"],
            "newOrderRespType": "RESULT",
        }
        if order["type"] == "LIMIT":
            params["timeInForce"] = "GTC"
            params["price"] = order["price"]

        result = self._request("POST", self.ORDER_ENDPOINT, params=params, signed=True)
        if not isinstance(result, dict):
            raise NetworkError("Unexpected order response: expected a JSON object.")
        return result
