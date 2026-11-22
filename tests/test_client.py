import unittest

import requests
from urllib.parse import parse_qs, urlparse

from trading_bot.client import BinanceFuturesTestnetClient
from trading_bot.exceptions import BinanceAPIError, NetworkError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.headers = {}
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class ClientTests(unittest.TestCase):
    def test_market_order_sends_signed_request(self):
        session = FakeSession(FakeResponse({
            "orderId": 12345, "status": "FILLED", "executedQty": "0.001", "avgPrice": "62000.00"
        }))
        client = BinanceFuturesTestnetClient("test-key", "test-secret", session=session)
        response = client.place_order({
            "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.001"
        })

        self.assertEqual(response["orderId"], 12345)
        call = session.calls[0]
        self.assertEqual(call["url"], "https://demo-fapi.binance.com/fapi/v1/order")
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["params"]["type"], "MARKET")
        self.assertNotIn("price", call["params"])
        self.assertIn("signature", call["params"])
        self.assertEqual(session.headers["X-MBX-APIKEY"], "test-key")

    def test_limit_order_includes_price_and_gtc(self):
        session = FakeSession(FakeResponse({"orderId": 67890, "status": "NEW", "executedQty": "0"}))
        client = BinanceFuturesTestnetClient("test-key", "test-secret", session=session)
        client.place_order({
            "symbol": "BTCUSDT", "side": "SELL", "type": "LIMIT", "quantity": "0.01", "price": "70000"
        })
        params = session.calls[0]["params"]
        self.assertEqual(params["price"], "70000")
        self.assertEqual(params["timeInForce"], "GTC")

    def test_base_url_is_demo(self):
        self.assertEqual(BinanceFuturesTestnetClient.BASE_URL, "https://demo-fapi.binance.com")


    def test_account_config_uses_signed_request(self):
        session = FakeSession(FakeResponse({"feeTier": 0, "canTrade": True}))
        client = BinanceFuturesTestnetClient("test-key", "test-secret", session=session)
        result = client.get_account_config()
        self.assertTrue(result["canTrade"])
        call = session.calls[0]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], "https://demo-fapi.binance.com/fapi/v1/accountConfig")
        self.assertIn("signature", call["params"])

    def test_exchange_info_uses_public_request(self):
        session = FakeSession(FakeResponse({"symbols": []}))
        client = BinanceFuturesTestnetClient("dummy", "dummy", session=session)
        result = client.get_exchange_info()
        self.assertEqual(result["symbols"], [])
        call = session.calls[0]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], "https://demo-fapi.binance.com/fapi/v1/exchangeInfo")
        self.assertNotIn("signature", call["params"])

    def test_server_error_marks_order_outcome_unknown(self):
        session = FakeSession(FakeResponse({"code": -1000, "msg": "Unknown error"}, status_code=503))
        client = BinanceFuturesTestnetClient("test-key", "test-secret", session=session)
        with self.assertRaises(BinanceAPIError) as caught:
            client.place_order({"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.001"})
        self.assertTrue(caught.exception.outcome_unknown)

    def test_transport_error_marks_order_outcome_unknown(self):
        class BrokenSession(FakeSession):
            def request(self, **kwargs):
                raise requests.Timeout("simulated timeout")

        client = BinanceFuturesTestnetClient("test-key", "test-secret", session=BrokenSession({}))
        with self.assertRaises(NetworkError) as caught:
            client.place_order({"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.001"})
        self.assertTrue(caught.exception.outcome_unknown)


if __name__ == "__main__":
    unittest.main()
