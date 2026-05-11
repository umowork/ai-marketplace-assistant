"""Wildberries parser — реальный парсинг карточек товаров и отзывов.

Использует:
- Публичное API card.wb.ru для карточек товаров
- Статистическое API suppliers-api.wildberries.ru для продаж (если есть ключ)
- Отзывы парсятся через wb-api-cdn
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

# Public API — не требует ключа
WB_CARD_API = "https://card.wb.ru/cards/v2/detail"
WB_FEEDBACK_API = "https://feedbacks1.wb.ru/feedbacks/v1/{subject}"
WB_QUESTIONS_API = "https://questions1.wb.ru/questions/v1/{subject}"
WB_PRICE_HISTORY_API = "https://basket-{}.wb.ru/vol{}/part{}/nm{}/info/price_history.json"

# Seller API — требует API-ключа
WB_SELLER_API = "https://suppliers-api.wildberries.ru"


class WildberriesParser(BaseParser):
    """Парсер Wildberries. Поддерживает публичный API (без ключа) и Seller API."""

    marketplace = "wb"

    def __init__(
        self,
        api_key: str = "",
        mock_mode: bool = False,
        cache: CacheBackend | None = None,
        http_timeout: int = 30,
    ):
        self.api_key = api_key
        self.mock_mode = mock_mode
        self.cache = cache or MemoryCache()
        self._http_timeout = http_timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._http_timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; MarketplaceAssistant/0.2)",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _request(self, url: str, headers: dict | None = None) -> dict[str, Any]:
        """Выполнить HTTP-запрос с обработкой ошибок."""
        client = await self._get_client()
        req_headers = headers or {}
        try:
            resp = await client.get(url, headers=req_headers, follow_redirects=True)
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
        """Получить карточку товара Wildberries по артикулу (nm ID).

        Использует публичное API карточки товара: card.wb.ru
        """
        if self.mock_mode:
            return self._mock_product_card(article)

        cache_key = self.cache.make_key("wb:product", article)
        cached = await self.cache.get(cache_key)
        if cached:
            return ProductCard(**cached)

        nm = _parse_wb_article(article)
        url = f"{WB_CARD_API}?nm={nm}&locale=ru"
        data = await self._request(url)

        products = data.get("data", {}).get("products", [])
        if not products:
            raise ProductNotFoundError(f"Товар {article} не найден на WB")

        raw = products[0]
        card = _build_wb_product_card(raw, article)

        await self.cache.set(cache_key, card.model_dump(mode="json"), ttl=600)
        return card

    async def get_feedbacks(
        self, article: str, limit: int = 100, offset: int = 0
    ) -> list[Feedback]:
        """Получить отзывы на товар через публичное API отзывов WB."""
        if self.mock_mode:
            return self._mock_feedbacks(article, limit)

        cache_key = self.cache.make_key("wb:feedbacks", article, str(limit), str(offset))
        cached = await self.cache.get(cache_key)
        if cached:
            return [Feedback(**fb) for fb in cached]

        nm = _parse_wb_article(article)
        # Определяем subject (поддомен) волны — нужно для правильного URL
        try:
            subject = _get_wb_subject(article)
        except Exception:
            subject = "1"

        url = f"{WB_FEEDBACK_API.format(subject=subject)}?nm={nm}&limit={limit}&offset={offset}"
        try:
            data = await self._request(url)
        except (ProductNotFoundError, MarketplaceAPIError):
            # Fallback: пробуем другие subject
            fallback_subjects = ["2", "3", "4", "5", "6"]
            for subj in fallback_subjects:
                if subj == subject:
                    continue
                try:
                    base = WB_FEEDBACK_API.format(subject=subj)
                    url = f"{base}?nm={nm}&limit={limit}&offset={offset}"
                    data = await self._request(url)
                    break
                except (ProductNotFoundError, MarketplaceAPIError):
                    continue
            else:
                return []

        feedbacks_raw = data.get("feedbacks", [])
        feedbacks = [_build_wb_feedback(fb, article) for fb in feedbacks_raw]

        await self.cache.set(
            cache_key, [fb.model_dump(mode="json") for fb in feedbacks], ttl=300
        )
        return feedbacks

    async def get_price_history(
        self, article: str, days: int = 30
    ) -> ProductPriceHistory:
        """Получить историю цены товара."""
        if self.mock_mode:
            return self._mock_price_history(article, days)

        cache_key = self.cache.make_key("wb:price_history", article, str(days))
        cached = await self.cache.get(cache_key)
        if cached:
            return ProductPriceHistory(**cached)

        nm = _parse_wb_article(article)
        # Формируем basket URL: vol/part/nm
        vol, part = _get_wb_volume_parts(nm)
        url = f"https://basket-{part}.wb.ru/vol{vol}/part{part}/nm{nm}/info/price_history.json"

        try:
            data = await self._request(url)
        except (ProductNotFoundError, MarketplaceAPIError) as e:
            logger.warning("Price history not available for %s: %s", article, e)
            return ProductPriceHistory(article=article, marketplace="wb", records=[])

        records = data if isinstance(data, list) else data.get("data", [])
        price_records = [
            {
                "date": datetime.fromtimestamp(r.get("dt", 0)).isoformat()
                if r.get("dt")
                else None,
                "price": Decimal(str(r.get("price", 0))),
                "discount": r.get("discount", 0),
            }
            for r in records[:days]
        ]

        history = ProductPriceHistory(
            article=article, marketplace="wb", records=price_records
        )
        await self.cache.set(cache_key, history.model_dump(mode="json"), ttl=900)
        return history

    async def search_competitors(
        self, query: str, limit: int = 10
    ) -> list[ProductCard]:
        """Поиск товаров на WB по поисковому запросу."""
        if self.mock_mode:
            return self._mock_competitors(query, limit)

        # Используем search API
        url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={query}&limit={limit}"
        try:
            data = await self._request(url)
        except MarketplaceAPIError:
            return []

        products_raw = data.get("data", {}).get("products", [])
        results = []
        for raw in products_raw[:limit]:
            try:
                card = _build_wb_product_card(raw, str(raw.get("id", "")))
                results.append(card)
            except Exception as e:
                logger.debug("Skipping competitor %s: %s", raw.get("id"), e)
                continue
        return results

    async def close(self) -> None:
        """Закрыть HTTP-сессию."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ===== Mock helpers (for mock_mode=True) =====

    def _mock_product_card(self, article: str) -> ProductCard:
        return ProductCard(
            marketplace="wb",
            article=article,
            name="Mock Товар WB",
            brand="MockBrand",
            category="Электроника",
            price=Decimal("1999.00"),
            old_price=Decimal("2499.00"),
            rating=4.3,
            reviews_count=127,
            stock=50,
            image_url=f"https://mock.wb.ru/img/{article}.jpg",
            description="Описание мок-товара для Wildberries.",
            characteristics={"Цвет": "Чёрный", "Размер": "M"},
        )

    def _mock_feedbacks(self, article: str, limit: int = 100) -> list[Feedback]:
        return [
            Feedback(
                id=f"fb-{article}-1",
                marketplace="wb",
                article=article,
                text="Отличный товар, качество на высоте!",
                rating=5,
                author="Иван",
                pros="Качество, доставка",
                likes=12,
            ),
            Feedback(
                id=f"fb-{article}-2",
                marketplace="wb",
                article=article,
                text="Нормально, но цена завышена.",
                rating=3,
                author="Мария",
                cons="Цена",
                likes=5,
            ),
        ]

    def _mock_price_history(self, article: str, days: int = 30) -> ProductPriceHistory:
        import random
        records = []
        base_price = 1999
        for day in range(min(days, 30)):
            records.append({
                "date": datetime.now().isoformat(),
                "price": Decimal(str(base_price + random.randint(-200, 200))),
                "discount": random.randint(0, 30),
            })
        return ProductPriceHistory(article=article, marketplace="wb", records=records)

    def _mock_competitors(self, query: str, limit: int = 10) -> list[ProductCard]:
        return [
            ProductCard(
                marketplace="wb",
                article=f"mock-comp-{i}",
                name=f"Конкурент {i}: {query}",
                brand="CompetitorBrand",
                price=Decimal(str(1500 + i * 100)),
                rating=4.0 + i * 0.1,
                reviews_count=50 + i * 10,
                stock=100 - i * 5,
            )
            for i in range(min(limit, 5))
        ]


# ===== Helper functions =====

def _parse_wb_article(article: str) -> str:
    """Извлечь nm ID из артикула (строковое или числовое значение)."""
    # WB артикул — это числовой nm ID
    article = article.strip().lstrip("0")
    if not article.isdigit():
        raise ParseError(f"Некорректный артикул WB: {article}. Ожидается числовой ID.")
    return article


def _get_wb_subject(article: str) -> str:
    """Определить subject (волну) для API отзывов WB."""
    nm = int(article)
    # Vol = nm // 100000
    vol = nm // 100000
    # Subject — это остаток от деления vol на количество subject-серверов
    # Типично 6 subject-серверов (1-6)
    subject = (vol % 6) + 1
    return str(subject)


def _get_wb_volume_parts(nm: int | str) -> tuple[int, int]:
    """Вычислить vol/part для URL карточки WB."""
    nm_int = int(nm)
    vol = nm_int // 100000
    part = nm_int // 1000
    return vol, part


def _build_wb_product_card(raw: dict, article: str) -> ProductCard:
    """Собрать ProductCard из сырых данных WB API."""
    try:
        price_raw = raw.get("sizes", [{}])[0].get("price", {}).get("total", 0)
        price = Decimal(str(price_raw)) / 100 if price_raw else Decimal("0")
        old_price_raw = raw.get("sizes", [{}])[0].get("price", {}).get("basic", 0)
        old_price = Decimal(str(old_price_raw)) / 100 if old_price_raw else None
    except (IndexError, TypeError, ValueError):
        price = Decimal("0")
        old_price = None

    # Извлекаем характеристики
    characteristics = {}
    for ch in raw.get("characteristics", []):
        if isinstance(ch, dict):
            characteristics[ch.get("name", "")] = ch.get("value", "")

    return ProductCard(
        marketplace="wb",
        article=article,
        name=raw.get("name", ""),
        brand=raw.get("brand", ""),
        category=raw.get("kind", ""),
        price=price,
        old_price=old_price,
        rating=float(raw.get("rating", 0) or 0),
        reviews_count=int(raw.get("feedbacks", 0) or 0),
        stock=int(raw.get("totalQuantity", 0) or 0),
        image_url=(
            f"https://basket-{raw.get('basket', '01')}.wb.ru"
            f"/vol{raw.get('vol', 0)}/part{raw.get('part', 0)}"
            f"/{raw.get('id', article)}/images/big/1.jpg"
        )
        if raw.get("id")
        else None,
        description=raw.get("description", ""),
        characteristics=characteristics,
    )


def _build_wb_feedback(raw: dict, article: str) -> Feedback:
    """Собрать Feedback из сырых данных WB API."""
    return Feedback(
        id=str(raw.get("id", "")),
        marketplace="wb",
        article=article,
        text=raw.get("text", ""),
        rating=int(raw.get("rating", 5)),
        author=raw.get("authorName", ""),
        date=_parse_wb_date(raw.get("createdDate")),
        pros=raw.get("pros", ""),
        cons=raw.get("cons", ""),
        likes=int(raw.get("likes", 0) or 0),
    )


def _parse_wb_date(date_str: str | None) -> datetime | None:
    """Парсинг даты из WB API."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None
