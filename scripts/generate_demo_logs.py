"""Generate visibly labeled MOCK API logs for documentation and evaluation.

These records exercise the real client/order code with a fake HTTP session.
They are not proof of orders executed on Binance. Run the CLI with testnet
credentials to produce genuine logs in logs/bot.log.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_bot.client import BinanceFuturesTestnetClient
from trading_bot.logging_config import configure_logging
from trading_bot.orders import OrderService


class DemoFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.demo_mode = "MOCKED_RESPONSE_NOT_LIVE_TESTNET"  # type: ignore[attr-defined]
        return True


class FakeResponse:
    status_code = 200
    ok = True
    text = "<mocked Binance JSON response>"

    def __init__(self, payload: dict):
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload: dict):
        self.payload = payload
        self.headers = {}

    def request(self, **kwargs):
        return FakeResponse(self.payload)


def generate(kind: str, order: dict[str, str], response: dict, destination: str) -> None:
    log_path = ROOT / destination
    log_path.unlink(missing_ok=True)
    configure_logging(log_path, "INFO")
    logger = logging.getLogger("trading_bot")
    for handler in logger.handlers:
        handler.addFilter(DemoFilter())

    client = BinanceFuturesTestnetClient(
        "DEMO_API_KEY_NOT_REAL", "DEMO_API_SECRET_NOT_REAL",
        session=FakeSession(response),
    )
    OrderService(client).submit_order(
        symbol=order["symbol"], side=order["side"], order_type=order["type"],
        quantity=order["quantity"], price=order.get("price"),
    )


if __name__ == "__main__":
    generate(
        "MARKET",
        {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.001"},
        {"symbol": "BTCUSDT", "orderId": 90000001, "status": "FILLED",
         "executedQty": "0.001", "avgPrice": "62000.00"},
        "logs/demo_market_order.log",
    )
    generate(
        "LIMIT",
        {"symbol": "BTCUSDT", "side": "SELL", "type": "LIMIT", "quantity": "0.001", "price": "70000"},
        {"symbol": "BTCUSDT", "orderId": 90000002, "status": "NEW",
         "executedQty": "0.000", "avgPrice": "0.00"},
        "logs/demo_limit_order.log",
    )
    print("Wrote MOCK-only sample logs to logs/demo_market_order.log and logs/demo_limit_order.log")
