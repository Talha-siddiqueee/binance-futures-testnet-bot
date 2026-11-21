"""Command-line interface for placing testnet futures orders."""

import argparse
import logging
import os
import sys
from getpass import getpass
from typing import Sequence

from dotenv import load_dotenv

from .client import BinanceFuturesTestnetClient
from .exceptions import BinanceAPIError, NetworkError, TradingBotError, ValidationError
from .logging_config import configure_logging
from .orders import OrderService

LOGGER = logging.getLogger("trading_bot.cli")
load_dotenv()  # Load local .env values when present; environment variables take precedence.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET and LIMIT orders on Binance USDⓈ-M Futures Testnet only.",
    )
    parser.add_argument("--symbol", help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", choices=("BUY", "SELL"), type=str.upper, help="Order side")
    parser.add_argument("--type", dest="order_type", choices=("MARKET", "LIMIT"), type=str.upper,
                        help="Order type")
    parser.add_argument("--quantity", help="Order quantity in base asset units")
    parser.add_argument("--price", help="Limit price; required for LIMIT orders")
    parser.add_argument("--interactive", action="store_true", help="Prompt for order details")
    parser.add_argument("--log-file", default="logs/bot.log", help="Log file path (default: logs/bot.log)")
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"),
                        help="Logging level")
    return parser


def _collect_interactive(args: argparse.Namespace) -> argparse.Namespace:
    print("\n=== Binance Futures Testnet Order ===")
    print("Environment: TESTNET (no mainnet endpoint is configured)\n")
    if not args.symbol:
        args.symbol = input("Symbol [BTCUSDT]: ").strip() or "BTCUSDT"
    if not args.side:
        args.side = input("Side (BUY/SELL): ").strip().upper()
    if not args.order_type:
        args.order_type = input("Order type (MARKET/LIMIT): ").strip().upper()
    if not args.quantity:
        args.quantity = input("Quantity: ").strip()
    if args.order_type == "LIMIT" and not args.price:
        args.price = input("Limit price: ").strip()
    return args


def _credentials() -> tuple[str, str]:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key:
        api_key = input("Binance Testnet API key: ").strip()
    if not api_secret:
        api_secret = getpass("Binance Testnet API secret: ").strip()
    if not api_key or not api_secret:
        raise TradingBotError("API key and secret are required. Set BINANCE_API_KEY and BINANCE_API_SECRET.")
    return api_key, api_secret


def _print_order_summary(order: dict[str, str]) -> None:
    print("\nOrder request summary")
    print("---------------------")
    print(f"Symbol:   {order['symbol']}")
    print(f"Side:     {order['side']}")
    print(f"Type:     {order['type']}")
    print(f"Quantity: {order['quantity']}")
    if "price" in order:
        print(f"Price:    {order['price']} (GTC)")


def _print_order_response(response: dict) -> None:
    print("\nBinance response")
    print("----------------")
    fields = ("orderId", "status", "executedQty", "avgPrice")
    for field in fields:
        value = response.get(field)
        print(f"{field}: {value if value not in (None, '') else 'N/A'}")
    print("\nSUCCESS: Order request accepted by Binance Futures Testnet.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_file, args.log_level)

    try:
        if args.interactive:
            args = _collect_interactive(args)

        missing = [name for name in ("symbol", "side", "order_type", "quantity") if not getattr(args, name)]
        if missing:
            parser.error("missing required arguments: " + ", ".join("--" + name.replace("_", "-") for name in missing))
        if args.order_type == "LIMIT" and not args.price:
            parser.error("--price is required when --type LIMIT")
        if args.order_type == "MARKET" and args.price is not None:
            parser.error("--price must not be supplied when --type MARKET")

        # Validate before prompting for credentials or making any network request.
        from .validators import validate_order
        normalized = validate_order(
            symbol=args.symbol, side=args.side, order_type=args.order_type,
            quantity=args.quantity, price=args.price,
        )
        print("Target: https://testnet.binancefuture.com (USDⓈ-M Futures Testnet)")
        _print_order_summary(normalized)
        api_key, api_secret = _credentials()
        client = BinanceFuturesTestnetClient(api_key, api_secret)
        service = OrderService(client)
        order, response = service.submit_order(**{
            "symbol": normalized["symbol"],
            "side": normalized["side"],
            "order_type": normalized["type"],
            "quantity": normalized["quantity"],
            "price": normalized.get("price"),
        })
        _print_order_response(response)
        return 0
    except (ValidationError, BinanceAPIError, NetworkError, TradingBotError, ValueError) as exc:
        unknown = getattr(exc, "outcome_unknown", False)
        event = "order_outcome_unknown" if unknown else "order_failure"
        LOGGER.error("Order outcome unknown" if unknown else "Order failed",
                     extra={"event": event, "error": str(exc)})
        prefix = "ORDER STATUS UNKNOWN" if unknown else "FAILURE"
        print(f"\n{prefix}: {exc}", file=sys.stderr)
        return 2 if unknown else 1
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:  # Last-resort guard; detail is retained in the log.
        LOGGER.exception("Unexpected application error", extra={"event": "unexpected_error", "error": str(exc)})
        print("\nFAILURE: Unexpected error. See the log file for details.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
