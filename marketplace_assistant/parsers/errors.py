"""Parser-specific errors."""


class ParseError(Exception):
    """Базовое исключение для ошибок парсинга."""


class ProductNotFoundError(ParseError):
    """Товар не найден на маркетплейсе."""


class MarketplaceAPIError(ParseError):
    """Ошибка при запросе к API маркетплейса."""

    def __init__(self, message: str, status_code: int = 0, response_text: str = ""):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(f"{message} [HTTP {status_code}]")


class RateLimitError(MarketplaceAPIError):
    """Превышен лимит запросов к API."""
