"""Streamlit UI for the Binance USDⓈ-M Futures Demo trading bot."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from trading_bot.client import BinanceFuturesTestnetClient
from trading_bot.exceptions import BinanceAPIError, NetworkError, TradingBotError, ValidationError
from trading_bot.logging_config import configure_logging
from trading_bot.orders import OrderService

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "logs" / "bot.log"
load_dotenv(ROOT / ".env")
configure_logging(LOG_PATH, "INFO")
LOGGER = logging.getLogger("trading_bot.ui")

st.set_page_config(
    page_title="Binance Futures Demo Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px;}
      [data-testid="stAppViewContainer"] {background: #0b1020;}
      [data-testid="stHeader"] {background: rgba(0,0,0,0);}
      [data-testid="stSidebar"] {background: #10182b; border-right: 1px solid #24304a;}
      .hero {padding: 1.25rem 1.5rem; border: 1px solid #263653; border-radius: 18px;
             background: linear-gradient(120deg, #15233e 0%, #111a2d 60%, #172b38 100%);}
      .hero-label {color: #8ea6c9; font-size: .78rem; letter-spacing: .12em; text-transform: uppercase;}
      .hero-title {color: #f3f6fc; font-size: 2rem; font-weight: 750; margin: .25rem 0;}
      .hero-copy {color: #a8b7ce; margin: 0;}
      .panel {padding: 1rem 1.1rem; border: 1px solid #263653; border-radius: 16px;
              background: #111a2d; margin-bottom: .8rem;}
      .muted {color: #94a3b8; font-size: .88rem;}
      div.stButton > button[kind="primary"] {border-radius: 10px; font-weight: 700; min-height: 3rem;}
      div[data-testid="stForm"] {border: 1px solid #263653; border-radius: 16px; padding: 1.1rem; background: #111a2d;}
      code {color: #9ed9ff;}
    </style>
    """,
    unsafe_allow_html=True,
)


def get_client() -> BinanceFuturesTestnetClient:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise TradingBotError(
            "Demo API credentials are missing. Add BINANCE_API_KEY and "
            "BINANCE_API_SECRET to your local .env file, then restart Streamlit."
        )
    return BinanceFuturesTestnetClient(api_key, api_secret)


def show_order_result(order: dict[str, str], response: dict[str, Any]) -> None:
    st.success("Binance Demo accepted the order request.")
    st.markdown("#### Order request summary")
    summary_cols = st.columns(4)
    summary = [
        ("Symbol", order["symbol"]),
        ("Side", order["side"]),
        ("Type", order["type"]),
        ("Quantity", order["quantity"]),
    ]
    if "price" in order:
        summary.append(("Limit price", order["price"]))
    for index, (label, value) in enumerate(summary):
        with summary_cols[index % len(summary_cols)]:
            st.metric(label, value)

    st.markdown("#### Binance order response")
    response_cols = st.columns(4)
    response_fields = [
        ("Order ID", response.get("orderId", "N/A")),
        ("Status", response.get("status", "N/A")),
        ("Executed quantity", response.get("executedQty", "N/A")),
        ("Average price", response.get("avgPrice") or "N/A"),
    ]
    for col, (label, value) in zip(response_cols, response_fields):
        with col:
            st.metric(label, str(value))

    status = str(response.get("status", "")).upper()
    if status in {"NEW", "PARTIALLY_FILLED"}:
        st.info("The order was accepted but is not fully filled. Check its status in the Demo trading account.")


def render_recent_logs() -> None:
    st.markdown("### Activity log")
    st.caption("Latest application log entries. API keys and signatures are not written to the log.")
    if not LOG_PATH.exists():
        st.info("No activity yet. Place an order or verify the API connection to create a log.")
        return
    try:
        lines = LOG_PATH.read_text(encoding="utf-8").splitlines()[-12:]
        st.code("\n".join(lines) if lines else "No log entries yet.", language="json")
    except OSError as exc:
        st.warning(f"Could not read the log file: {exc}")


st.markdown(
    """
    <div class="hero">
      <div class="hero-label">USDⓈ-M Futures · Demo environment</div>
      <div class="hero-title">Trading Terminal</div>
      <p class="hero-copy">Place and inspect MARKET and LIMIT orders using your Binance Demo API credentials.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

api_ready = bool(os.getenv("BINANCE_API_KEY", "").strip() and os.getenv("BINANCE_API_SECRET", "").strip())
with st.sidebar:
    st.markdown("## Connection")
    st.markdown("**Environment:** Binance Futures Demo")
    st.markdown("**REST host:** `demo-fapi.binance.com`")
    st.markdown(
        f"**Credentials:** {'🟢 Configured' if api_ready else '🔴 Missing'}"
    )
    st.link_button("Open Binance Demo", "https://demo.binance.com/en/futures/BTCUSDT", use_container_width=True)
    st.divider()
    st.markdown("### Safety")
    st.caption("This app is configured for the Demo REST host. Never put production API keys in this project's .env file.")
    st.caption("A network timeout can leave an order outcome unknown. Check Demo order history before retrying.")
    if st.button("Verify API connection", use_container_width=True):
        try:
            config = get_client().get_account_config()
            st.session_state["account_config"] = config
            st.success("Authenticated connection successful.")
            LOGGER.info("Demo API connection verified", extra={"event": "account_connection_success"})
        except (BinanceAPIError, NetworkError, TradingBotError, ValueError) as exc:
            LOGGER.error("Demo API connection failed", extra={"event": "account_connection_failure", "error": str(exc)})
            st.error(str(exc))
    account_config = st.session_state.get("account_config")
    if account_config:
        st.markdown("**Account check**")
        st.write(f"Can trade: {'Yes' if account_config.get('canTrade') else 'No'}")
        st.write(f"Fee tier: {account_config.get('feeTier', 'N/A')}")

order_col, log_col = st.columns([1.05, 0.95], gap="large")

with order_col:
    st.markdown("### Place an order")
    st.caption("All orders are sent to Binance Futures Demo, not the live trading environment.")
    with st.form("order_form", clear_on_submit=False):
        symbol = st.text_input("Symbol", value="BTCUSDT", help="Example: BTCUSDT")
        side = st.radio("Side", options=["BUY", "SELL"], horizontal=True)
        order_type = st.radio("Order type", options=["MARKET", "LIMIT"], horizontal=True)
        quantity = st.text_input("Quantity", value="0.001", help="Quantity in the base asset, e.g. BTC")
        price: str | None = None
        if order_type == "LIMIT":
            price_input = st.text_input("Limit price (USDT)", value="", placeholder="Enter limit price", help="Required for LIMIT orders")
            price = price_input.strip() or None
        confirmed = st.checkbox("I confirm this order is being sent to the Binance Demo environment.")
        submitted = st.form_submit_button("Place Demo order", type="primary", use_container_width=True)

    if submitted:
        st.session_state.pop("last_order", None)
        if not confirmed:
            st.warning("Please confirm the Demo environment before submitting.")
        else:
            try:
                client = get_client()
                service = OrderService(client)
                order, response = service.submit_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                )
                st.session_state["last_order"] = {"order": order, "response": response}
            except ValidationError as exc:
                LOGGER.warning("UI order validation failed", extra={"event": "ui_validation_error", "error": str(exc)})
                st.error(f"Input validation failed: {exc}")
            except (BinanceAPIError, NetworkError) as exc:
                LOGGER.error("UI order submission failed", extra={"event": "ui_order_failure", "error": str(exc)})
                if getattr(exc, "outcome_unknown", False):
                    st.error(f"Order outcome UNKNOWN: {exc}")
                    st.warning("Do not submit again yet. Check your Binance Demo order history first.")
                else:
                    st.error(f"Order failed: {exc}")
            except (TradingBotError, ValueError) as exc:
                st.error(str(exc))
            except Exception as exc:  # UI boundary: keep unexpected details in the application log.
                LOGGER.exception("Unexpected UI error", extra={"event": "ui_unexpected_error", "error": str(exc)})
                st.error("Unexpected application error. Check logs/bot.log for details.")

    last_order = st.session_state.get("last_order")
    if last_order:
        show_order_result(last_order["order"], last_order["response"])

with log_col:
    render_recent_logs()
    st.markdown("### Quick guide")
    st.markdown(
        "- **MARKET:** submits at the available market price.\n"
        "- **LIMIT:** submits a GTC limit order using your specified price.\n"
        "- **BUY / SELL:** selects the order side.\n"
        "- The application validates basic input and Binance performs final exchange-rule checks."
    )

st.divider()
st.caption("Educational project · Binance Futures Demo only · No production endpoint is configured")
