# Binance Futures Testnet Order Bot (USDⓈ-M)

A small, reusable Python 3 CLI for submitting **MARKET** and **LIMIT** BUY/SELL orders to the Binance USDⓈ-M Futures Testnet. It uses direct signed REST requests, validates inputs before network access, and writes structured JSON-lines logs.

> **Testnet safety:** The client is pinned to the exact host required by this task: `https://testnet.binancefuture.com`. It does not contain a production URL or a mainnet switch. Use only API credentials created for the Futures Testnet. **Endpoint compatibility note:** Binance's currently published general USDⓈ-M Futures documentation lists `https://demo-fapi.binance.com` as the Testnet REST base for its newer Demo environment. This project deliberately retains the host specified in this assignment; verify that your testnet account is provisioned for that host before submitting orders. Futures trading is risky even on test environments; this project is an educational API exercise, not investment advice.

## Features

- MARKET and LIMIT orders; BUY and SELL sides.
- CLI flags or an interactive prompt.
- Positive finite decimal validation, symbol/side/type checks, and LIMIT price requirement.
- HMAC-SHA256 signed requests, configurable timeout, and `recvWindow`.
- Handles Binance API errors, HTTP failures, invalid responses, and network errors. Ambiguous transport/5XX outcomes are reported as UNKNOWN (not a definite failure) to discourage duplicate resubmissions.
- JSON-lines logs for requests, responses, and errors. API keys and signatures are not written to logs.
- Unit tests that run without a Binance account or network access.

## Project structure

```text
binance_futures_testnet_bot/
├── trading_bot/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                 # CLI and interactive prompts
│   ├── client.py              # Signed Binance REST client
│   ├── exceptions.py          # Application/API/network exceptions
│   ├── logging_config.py      # JSON-lines logging
│   ├── orders.py              # Reusable order service
│   └── validators.py          # Input validation and normalization
├── tests/
│   ├── test_client.py
│   └── test_validators.py
├── scripts/
│   └── generate_demo_logs.py
├── logs/
│   ├── demo_market_order.log
│   └── demo_limit_order.log
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

1. Create and activate a Binance USDⓈ-M Futures Testnet account at the Binance Futures Testnet site.
2. Create an API key/secret for that **testnet** account and enable the required Futures trading permission.
3. Install Python 3.10+ (the source uses modern type annotations) and create a virtual environment:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Create a local `.env` file from the example and fill in your **testnet** credentials:

   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env
   # macOS/Linux
   cp .env.example .env
   ```

   Set `BINANCE_API_KEY` and `BINANCE_API_SECRET` in `.env`. The `.env` file is ignored by Git. Never commit credentials or paste them into source code.

## Run examples

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

A LIMIT order is submitted with `timeInForce=GTC`. The sample values are illustrative; check the Testnet's symbol filters, minimum quantity/notional, and current market before submitting.

### Interactive mode

```bash
python -m trading_bot --interactive
```

### Logging options

By default, output is written to `logs/bot.log`. Choose a different file or verbosity with:

```bash
python -m trading_bot --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 \
  --log-file logs/market_run.log --log-level DEBUG
```

Each log line is a JSON object. Request logs omit the HMAC signature; the API key is sent only in the HTTP header and is not logged. Do not share live logs publicly without reviewing them first.

## Output

The CLI prints the normalized request summary and these response fields when Binance provides them:

- `orderId`
- `status`
- `executedQty`
- `avgPrice`

A successful HTTP response means Binance accepted the order request. It does not necessarily mean a LIMIT order was filled; check the returned `status` (`NEW`, `FILLED`, etc.).

## Tests

The tests use a fake HTTP session; they do not place live orders and do not need API credentials:

```bash
python -m unittest discover -s tests -v
```

## Included order log files: important note

`logs/demo_market_order.log` and `logs/demo_limit_order.log` are **synthetic demonstration logs** produced through the real client/order code with a mocked HTTP response. Every line contains `demo_mode: MOCKED_RESPONSE_NOT_LIVE_TESTNET`. They are included to demonstrate the request/response logging format, **not** to claim that orders were executed on Binance.

To create genuine order logs, configure valid Testnet credentials and run the MARKET and LIMIT examples above. The real API request and response records will be written to `logs/bot.log`. Keep that file private unless you have checked it for sensitive information.

## Assumptions and limitations

- This is USDⓈ-M Futures, not Spot or COIN-M Futures.
- The required host is fixed to `https://testnet.binancefuture.com`; requests use `/fapi/v1/order`.
- LIMIT orders use GTC by default. MARKET orders do not accept a price argument.
- The app validates basic formatting and positive numeric values. It does not hard-code symbol-specific `tickSize`, `stepSize`, minimum quantity, or notional rules; Binance validates those and returns an API error when an order violates exchange filters.
- The app does not set leverage, margin mode, position mode, or reduce-only flags. It uses the account's existing Futures configuration (one-way mode is the default assumption).
- If a transport failure or HTTP 5XX occurs after submission, the app reports the outcome as UNKNOWN. Check Testnet order history before trying again; an order may have reached the matching engine even if the client did not receive confirmation.
- The local computer clock must be reasonably synchronized because signed endpoints require a millisecond timestamp.
- No retries are made automatically for order placement to avoid accidentally duplicating a trade after an ambiguous network timeout.

## API reference

- [Binance USDⓈ-M Futures REST API — New Order](https://developers.binance.me/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade)
- [Binance Futures API general information](https://developers.binance.me/en/docs/products/derivatives-trading-usds-futures/general-info)
- [Binance official signature examples](https://github.com/binance/binance-signature-examples)
