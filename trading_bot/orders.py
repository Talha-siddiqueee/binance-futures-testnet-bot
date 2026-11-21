"""Order orchestration independent of the CLI."""

import logging
from typing import Any

from .client import BinanceFuturesTestnetClient
from .validators import validate_order

LOGGER = logging.getLogger("trading_bot.orders")


class OrderService:
    def __init__(self, client: BinanceFuturesTestnetClient) -> None:
        self.client = client

    def submit_order(
        self, *, symbol: str, side: str, order_type: str,
        quantity: str, price: str | None = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        order = validate_order(
            symbol=symbol, side=side, order_type=order_type,
            quantity=quantity, price=price,
        )
        LOGGER.info("Submitting order", extra={"event": "order_submit", "params": order})
        response = self.client.place_order(order)
        LOGGER.info(
            "Order submitted",
            extra={"event": "order_success", "response": response},
        )
        return order, response
