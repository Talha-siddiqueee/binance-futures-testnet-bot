import unittest

from trading_bot.exceptions import ValidationError
from trading_bot.validators import validate_order


class ValidatorTests(unittest.TestCase):
    def test_market_order_normalizes_values(self):
        result = validate_order(
            symbol="btcusdt", side="buy", order_type="market", quantity="0.00100"
        )
        self.assertEqual(result, {
            "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.001"
        })

    def test_limit_order_requires_and_normalizes_price(self):
        result = validate_order(
            symbol="BTCUSDT", side="SELL", order_type="LIMIT", quantity="0.01", price="65000.000"
        )
        self.assertEqual(result["price"], "65000")

    def test_limit_order_without_price_fails(self):
        with self.assertRaisesRegex(ValidationError, "Price is required"):
            validate_order(symbol="BTCUSDT", side="BUY", order_type="LIMIT", quantity="0.01")

    def test_market_order_with_price_fails(self):
        with self.assertRaisesRegex(ValidationError, "Do not provide --price"):
            validate_order(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.01", price="1")

    def test_invalid_side_fails(self):
        with self.assertRaises(ValidationError):
            validate_order(symbol="BTCUSDT", side="HOLD", order_type="MARKET", quantity="1")

    def test_non_positive_quantity_fails(self):
        with self.assertRaises(ValidationError):
            validate_order(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0")

    def test_nan_quantity_fails(self):
        with self.assertRaises(ValidationError):
            validate_order(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="NaN")


if __name__ == "__main__":
    unittest.main()
