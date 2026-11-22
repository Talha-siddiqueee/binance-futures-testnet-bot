# Binance Futures Demo Trading Bot (USDⓈ-M)

A small, reusable Python application for placing **MARKET** and **LIMIT** BUY/SELL orders on Binance USDⓈ-M Futures **Demo**. It includes both a command-line interface (CLI) and a lightweight Streamlit web UI. The application uses direct signed REST requests, validates user input, handles API/network failures, and writes structured JSON-lines logs.

> **Demo-only safety:** The REST client is pinned to `https://demo-fapi.binance.com`. No production/mainnet endpoint or environment switch is provided. Create API credentials in Binance Futures Demo API Management only. Never put live/mainnet credentials in this project. A successful order response does not guarantee a LIMIT order has filled; check the returned status.

## Features

- MARKET and LIMIT orders with both BUY and SELL sides.
- CLI with `argparse` flags and interactive prompts.
- Streamlit UI with order form, Demo API connection check, request summary, response metrics, and recent log viewer.
- Input validation for symbol format, side, type, finite positive quantity, and required LIMIT price.
- HMAC-SHA256 signed requests, timestamp, configurable receive window, and HTTP timeout.
- Reusable API methods for account configuration, exchange information, and order placement.
- JSON-lines logs for API requests, responses, order outcomes, and errors. API keys and signatures are not logged.
- Explicit handling for ambiguous timeout/5XX order outcomes. The app does not automatically retry order placement.
- Unit tests use mocked HTTP sessions and do not need credentials or place real Demo orders.

## Project structure

```text
binance_futures_testnet_bot/
├── app.py                       # Streamlit web UI
├── trading_bot/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                    # CLI and interactive prompts
│   ├── client.py                 # Signed Binance Demo REST client
│   ├── exceptions.py             # Application/API/network exceptions
│   ├── logging_config.py         # JSON-lines logging
│   ├── orders.py                 # Reusable order service
│   └── validators.py             # Input validation and normalization
├── tests/
│   ├── test_client.py
│   └── test_validators.py
├── scripts/
│   └── generate_demo_logs.py
├── logs/
│   ├── demo_market_order.log      # Mock example, not a live execution
│   └── demo_limit_order.log       # Mock example, not a live execution
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

1. Create/sign in to a Binance account and open the **Futures Demo Trading** environment: <https://demo.binance.com/en/futures/BTCUSDT>.
2. Generate an API key and secret in the Demo environment's API Management. Use a key type supported by this project's HMAC-SHA256 signer. Do not use Live/production API credentials.
3. Install Python 3.10 or newer and create a virtual environment:

   ```powershell
   # Windows PowerShell
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # macOS/Linux
   source .venv/bin/activate
   ```

4. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

5. Create the local environment file:

   ```powershell
   # Windows PowerShell
   Copy-Item .env.example .env
   notepad .env
   ```

   Set the two values in `.env` to your **Demo** credentials:

   ```dotenv
   BINANCE_API_KEY=your_demo_api_key
   BINANCE_API_SECRET=your_demo_api_secret
   ```

   `.env` is excluded by `.gitignore`. Never commit it or paste credentials into source code, screenshots, chat, or README files.

## Run the web UI (bonus)

From the project root, with the virtual environment activated:

```bash
streamlit run app.py
```

Streamlit prints a local URL (normally `http://localhost:8501`) and opens the dashboard in your browser. The UI provides:

- Symbol, BUY/SELL, MARKET/LIMIT, quantity, and conditional LIMIT price inputs.
- A confirmation checkbox before submitting a Demo order.
- A read-only **Verify API connection** action.
- Order request summary and response fields (`orderId`, `status`, `executedQty`, `avgPrice`).
- Recent JSON log entries.

The dashboard is a local application; do not expose it publicly or run it on an untrusted shared machine while credentials are configured.

## Run the CLI

Run commands from the project root.

### MARKET BUY

```bash
python -m trading_bot --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### MARKET SELL

```bash
python -m trading_bot --symbol BTCUSDT --side SELL --type MARKET --quantity 0.001
```

### LIMIT BUY

```bash
python -m trading_bot --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 60000
```

### LIMIT SELL

```bash
python -m trading_bot --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000
```

LIMIT orders use `timeInForce=GTC`. Example quantities/prices are illustrative. Check the symbol's current filters, minimum quantity/notional, available Demo balance, and current market before submitting an order.

### Interactive CLI

```bash
python -m trading_bot --interactive
```

### Logging options

The default log file is `logs/bot.log`:

```bash
python -m trading_bot --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --log-level DEBUG
```

Each log line is a JSON object. Request logs omit the HMAC signature; the API key is sent only in the HTTP header and is not logged. Review logs before sharing them publicly.

## Output

The CLI and UI display the normalized order request and these response fields when Binance returns them:

- `orderId`
- `status`
- `executedQty`
- `avgPrice`

A successful HTTP response means Binance accepted the order request. A LIMIT order can remain `NEW` until it fills.

## Tests

The tests use fake HTTP sessions. They do not place orders and do not require API credentials:

```bash
python -m unittest discover -s tests -v
```

## Included log files

`logs/demo_market_order.log` and `logs/demo_limit_order.log` are **synthetic demonstration logs** produced with mocked HTTP responses. They are not proof of live Demo executions. Genuine request/response logs are written to `logs/bot.log` after running the CLI or UI with Demo credentials.

## Assumptions and limitations

- This project targets USDⓈ-M Futures Demo, not Spot, COIN-M Futures, or Live/mainnet.
- The REST base URL is fixed to `https://demo-fapi.binance.com`; order placement uses `POST /fapi/v1/order`.
- LIMIT orders use GTC. MARKET orders do not accept a price parameter.
- The application performs basic local input validation. Binance remains the final authority for symbol trading status, precision, tick size, quantity steps, minimum notional, balance, and other account/exchange restrictions; invalid orders are returned as API errors and logged.
- The app does not set leverage, margin mode, position mode, or reduce-only flags. It uses the Demo account's existing Futures configuration.
- If a transport failure or HTTP 5XX happens after submission, the app reports the outcome as UNKNOWN. Check Demo order history before retrying because the order may have reached the matching engine even if the client did not receive the response.
- The local computer clock must be reasonably synchronized because signed endpoints require a millisecond timestamp.
- No automatic retries are made for order placement to avoid duplicate trades after ambiguous timeouts.

## API references

- [Binance USDⓈ-M Futures general information and Demo base URL](https://developers.binance.me/en/docs/products/derivatives-trading-usds-futures/general-info)
- [Binance USDⓈ-M Futures New Order API](https://developers.binance.me/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade)
- [Binance official signature examples](https://github.com/binance/binance-signature-examples)
