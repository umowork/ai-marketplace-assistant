"""Ozon parser — реальный парсинг карточек товаров и отзывов.

Использует:
- Публичное API ozon.ru для карточек товаров (через ozon-product-page)
- Seller API (api-seller.ozon.ru) для детальных данных (если есть ключи)
- Отзывы через публичный endpoint
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from marketplace_assistant.models.feedback import Feedback
from marketplace_assistant.models.product import ProductCard, ProductPriceHistory
from marketplace_assistant.parsers.base import BaseParser
from marketplace_assistant.parsers.errors import (
    MarketplaceAPIError,
    ParseError,
    ProductNotFoundError,
    RateLimitError,
)
from marketplace_assistant.utils.cache import CacheBackend, MemoryCache
from marketplace_assistant.utils.logger import get_logger

logger = get_logger(__name__)

# Публичные API Ozon (без ключа)
OZON_PRODUCT_API = "https://api.ozon.ru/product"
OZON_SELLER_API = "https://api-seller.ozon.ru"

# Endpoints
OZON_PRODUCT_DETAIL = f"{OZON_PRODUCT_API}/detail"
OZON_REVIEWS_API = "https://www.ozon.ru/api/detail/reviews"


class OzonParser(BaseParser):
    """Парсер Ozon. Поддерживает публичный API и Seller API."""

    marketplace = "ozon"

    def __init__(
        self,
        client_id: str = "",
        api_key: str = "",
        mock_mode: bool = False,
        cache: CacheBackend | None = None,
        http_timeout: int = 30,
    ):
        self.client_id = client_id
        self.api_key = api_key
        self.mock_mode = mock_mode
        self.cache = cache or MemoryCache()
        self._http_timeout = http_timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; MarketplaceAssistant/0.2)",
                "Accept": "application/json",
            }
            if self.client_id and self.api_key:
                headers["Client-Id"] = self.client_id
                headers["Api-Key"] = self.api_key
            self._client = httpx.AsyncClient(
                timeout=self._http_timeout, headers=headers
            )
        return self._client

    async def _request(
        self, url: str, method: str = "GET", json_data: dict | None = None
    ) -> dict[str, Any]:
        """Выполнить HTTP-запрос."""
        client = await self._get_client()
        try:
            if method == "POST":
                resp = await client.post(url, json=json_data or {})
            else:
                resp = await client.get(url, params=json_data)
        except httpx.TimeoutException as e:
            raise MarketplaceAPIError("Request timeout", status_code=0) from e
        except httpx.HTTPError as e:
            raise MarketplaceAPIError(str(e), status_code=0) from e

        if resp.status_code == 429:
            raise RateLimitError("Rate limit exceeded", status_code=429)
        if resp.status_code == 404:
            raise ProductNotFoundError(f"Product not found at {url}")
        if resp.status_code >= 500:
            raise MarketplaceAPIError(
                "Server error", status_code=resp.status_code, response_text=resp.text
            )

        try:
            return resp.json()
        except Exception as e:
            raise ParseError(f"Invalid JSON response: {e}") from e

    async def get_product_card(self, article: str) -> ProductCard:
        """Получить карточку товара Ozon по артикулу (FBO SKU или FBS SKU)."""
        if self.mock_mode:
            return self._mock_product_card(article)

        cache_key = self.cache.make_key("ozon:product", article)
        cached = await self.cache.get(cache_key)
        if cached:
            return ProductCard(**cached)

        sku = _parse_ozon_article(article)
        # Пробуем Seller API если есть ключи
        if self.client_id and self.api_key:
            try:
                card = await self._get_product_via_seller_api(sku)
                await self.cache.set(cache_key, card.model_dump(mode="json"), ttl=600)
                return card
            except (MarketplaceAPIError, ProductNotFoundError) as e:
                logger.debug("Seller API failed for %s: %s, trying public API", article, e)

        # Публичный API — парсинг страницы товара
        card = await self._get_product_via_public_api(sku, article)
        await self.cache.set(cache_key, card.model_dump(mode="json"), ttl=600)
        return card

    async def _get_product_via_seller_api(self, sku: str) -> ProductCard:
        """Получить карточку через Seller API Ozon."""
        url = f"{OZON_SELLER_API}/v2/product/info"
        data = await self._request(url, method="POST", json_data={"sku": int(sku)})

        result = data.get("result", {})
        if not result:
            raise ProductNotFoundError(f"Товар {sku} не найден в Ozon Seller API")

        price = Decimal("0")
        old_price = None
        price_data = result.get("price", {})
        if price_data:
            price = Decimal(str(price_data.get("price", "0")))
            old_price_raw = price_data.get("old_price")
            if old_price_raw:
                old_price = Decimal(str(old_price_raw))

        characteristics = {}
        for attr in result.get("attributes", []):
            if isinstance(attr, dict):
                characteristics[attr.get("name", "")] = attr.get("value", "")

        return ProductCard(
            marketplace="ozon",
            article=sku,
            name=result.get("name", ""),
            brand=result.get("brand", ""),
            category=result.get("category", ""),
            price=price,
            old_price=old_price,
            rating=float(result.get("rating", 0) or 0),
            reviews_count=int(result.get("reviews_count", 0) or 0),
            stock=int(result.get("stock", {}).get("present", 0) or 0),
            image_url=result.get("primary_image", ""),
            description=result.get("description", ""),
            characteristics=characteristics,
        )

    async def _get_product_via_public_api(
        self, sku: str, article: str
    ) -> ProductCard:
        """Получить карточку через публичный API (парсинг страницы)."""
        # Ozon public product detail
        url = f"https://www.ozon.ru/api/v2/product/{sku}/details"
        try:
            data = await self._request(url)
        except MarketplaceAPIError as e:
            raise ProductNotFoundError(f"Товар {article} не найден на Ozon") from e

        result = data.get("data", {})

        price = Decimal("0")
        price_data = result.get("priceInfo", {}) or {}
        try:
            price = Decimal(str(price_data.get("currentPrice", "0")))
        except (ValueError, TypeError):
            pass

        return ProductCard(
            marketplace="ozon",
            article=sku,
            name=result.get("name", article),
            brand=result.get("brand", ""),
            price=price,
            rating=float(result.get("rating", 0) or 0),
            reviews_count=int(result.get("feedbacks", 0) or 0),
            image_url=result.get("imageUrl", ""),
            description=result.get("description", ""),
        )

    async def get_feedbacks(
        self, article: str, limit: int = 100, offset: int = 0
    ) -> list[Feedback]:
        """Получить отзывы на товар Ozon."""
        if self.mock_mode:
            return self._mock_feedbacks(article, limit)

        cache_key = self.cache.make_key("ozon:feedbacks", article, str(limit), str(offset))
        cached = await self.cache.get(cache_key)
        if cached:
            return [Feedback(**fb) for fb in cached]

        sku = _parse_ozon_article(article)
        # Публичное API отзывов Ozon (ограниченный доступ)
        url = f"{OZON_REVIEWS_API}?sku={sku}&limit={limit}&offset={offset}"
        try:
            data = await self._request(url)
        except MarketplaceAPIError:
            # Пробуем seller API если доступен
            if self.client_id and self.api_key:
                return await self._get_feedbacks_via_seller_api(sku, limit, offset)
            return []

        feedbacks_raw = data.get("reviews", [])
        feedbacks = [_build_ozon_feedback(fb, article) for fb in feedbacks_raw]

        await self.cache.set(
            cache_key, [fb.model_dump(mode="json") for fb in feedbacks], ttl=300
        )
        return feedbacks

    async def _get_feedbacks_via_seller_api(
        self, sku: str, limit: int, offset: int
    ) -> list[Feedback]:
        """Отзывы через Seller API Ozon."""
        url = f"{OZON_SELLER_API}/v2/product/reviews/list"
        data = await self._request(
            url,
            method="POST",
            json_data={"sku": int(sku), "limit": limit, "offset": offset},
        )
        result = data.get("result", {})
        feedbacks_raw = result.get("reviews", [])
        return [_build_ozon_feedback(fb, sku) for fb in feedbacks_raw]

    async def get_price_history(
        self, article: str, days: int = 30
    ) -> ProductPriceHistory:
        """Получить историю цены Ozon товара."""
        if self.mock_mode:
            return self._mock_price_history(article, days)

        # Ozon не предоставляет публичной истории цен
        # Возвращаем пустую историю
        logger.info("Ozon price history not available publicly for %s", article)
        return ProductPriceHistory(article=article, marketplace="ozon", records=[])

    async def search_competitors(
        self, query: str, limit: int = 10
    ) -> list[ProductCard]:
        """Поиск товаров на Ozon."""
        if self.mock_mode:
            return self._mock_competitors(query, limit)

        # Используем поисковый API Ozon
        url = f"https://www.ozon.ru/api/v2/search?text={query}&limit={limit}"
        try:
            data = await self._request(url)
        except MarketplaceAPIError:
            return []

        products_raw = data.get("data", {}).get("items", [])
        results = []
        for raw in products_raw[:limit]:
            try:
                card = ProductCard(
                    marketplace="ozon",
                    article=str(raw.get("id", "")),
                    name=raw.get("title", ""),
                    price=Decimal(str(raw.get("price", "0"))),
                    rating=float(raw.get("rating", 0) or 0),
                    reviews_count=int(raw.get("reviewsCount", 0) or 0),
                )
                results.append(card)
            except Exception:
                continue
        return results

    async def close(self) -> None:
        """Закрыть HTTP-сессию."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ===== Mock helpers =====

    def _mock_product_card(self, article: str) -> ProductCard:
        return ProductCard(
            marketplace="ozon",
            article=article,
            name="Mock Товар Ozon",
            brand="OzonMock",
            category="Косметика",
            price=Decimal("1299.00"),
            rating=4.5,
            reviews_count=89,
            stock=30,
            description="Мок-описание товара Ozon.",
        )

    def _mock_feedbacks(self, article: str, limit: int = 100) -> list[Feedback]:
        return [
            Feedback(
                id=f"oz-fb-{article}-1",
                marketplace="ozon",
                article=article,
                text="Хороший товар, соответствует описанию.",
                rating=4,
                author="Анна",
                pros="Качество, упаковка",
                likes=8,
            ),
            Feedback(
                id=f"oz-fb-{article}-2",
                marketplace="ozon",
                article=article,
                text="Не подошёл по размеру, вернула.",
                rating=2,
                author="Елена",
                cons="Размер не соответствует",
                likes=3,
            ),
        ]

    def _mock_price_history(self, article: str, days: int = 30) -> ProductPriceHistory:
        import random
        records = []
        base_price = 1299
        for day in range(min(days, 30)):
            records.append({
                "date": datetime.now().isoformat(),
                "price": Decimal(str(base_price + random.randint(-100, 100))),
                "discount": random.randint(0, 20),
            })
        return ProductPriceHistory(article=article, marketplace="ozon", records=records)

    def _mock_competitors(self, query: str, limit: int = 10) -> list[ProductCard]:
        return [
            ProductCard(
                marketplace="ozon",
                article=f"oz-mock-comp-{i}",
                name=f"Ozon Конкурент {i}: {query}",
                price=Decimal(str(1100 + i * 100)),
                rating=4.0 + i * 0.15,
                reviews_count=30 + i * 5,
            )
            for i in range(min(limit, 5))
        ]


# ===== Helper functions =====

def _parse_ozon_article(article: str) -> str:
    """Извлечь SKU из артикула Ozon."""
    article = article.strip()
    if not article.isdigit():
        raise ParseError(f"Некорректный артикул Ozon: {article}. Ожидается числовой SKU.")
    return article


def _build_ozon_feedback(raw: dict, article: str) -> Feedback:
    """Собрать Feedback из сырых данных Ozon API."""
    return Feedback(
        id=str(raw.get("id", "")),
        marketplace="ozon",
        article=article,
        text=raw.get("text", ""),
        rating=int(raw.get("rating", 5)),
        author=raw.get("author", {}).get("name", "") if isinstance(raw.get("author"), dict) else "",
        date=_parse_ozon_date(raw.get("createdAt") or raw.get("date")),
        pros=raw.get("pros", ""),
        cons=raw.get("cons", ""),
        likes=int(raw.get("likes", 0) or 0),
    )


def _parse_ozon_date(date_str: str | None) -> datetime | None:
    """Парсинг даты из Ozon API."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None
