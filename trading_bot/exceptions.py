"""Application-specific exception types."""


class TradingBotError(Exception):
    """Base exception for expected application errors."""


class ValidationError(TradingBotError):
    """Raised when CLI order input is invalid."""


class BinanceAPIError(TradingBotError):
    """Raised when Binance responds with an API or HTTP error."""

    def __init__(self, message: str, *, code: int | None = None, http_status: int | None = None, outcome_unknown: bool = False):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.outcome_unknown = outcome_unknown


class NetworkError(TradingBotError):
    """Raised when the API cannot be reached or its response cannot be read."""

    def __init__(self, message: str, *, outcome_unknown: bool = False):
        super().__init__(message)
        self.outcome_unknown = outcome_unknown
