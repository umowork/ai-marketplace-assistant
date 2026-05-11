"""Base parser interface for all marketplace parsers."""

from abc import ABC, abstractmethod

from marketplace_assistant.models.feedback import Feedback, FeedbackSummary
from marketplace_assistant.models.product import ProductCard, ProductPriceHistory


class BaseParser(ABC):
    """Абстрактный базовый класс для парсеров маркетплейсов."""

    marketplace: str = ""

    @abstractmethod
    async def get_product_card(self, article: str) -> ProductCard:
        """Получить карточку товара по артикулу."""
        ...

    @abstractmethod
    async def get_feedbacks(
        self, article: str, limit: int = 100, offset: int = 0
    ) -> list[Feedback]:
        """Получить отзывы на товар."""
        ...

    @abstractmethod
    async def get_price_history(
        self, article: str, days: int = 30
    ) -> ProductPriceHistory:
        """Получить историю изменения цены."""
        ...

    async def get_feedback_summary(
        self, article: str, limit: int = 100
    ) -> FeedbackSummary:
        """Получить сводку по отзывам (базовая реализация)."""
        feedbacks = await self.get_feedbacks(article, limit=limit)
        if not feedbacks:
            return FeedbackSummary(
                article=article,
                marketplace=self.marketplace,
                total_reviews=0,
                average_rating=0.0,
            )

        total = len(feedbacks)
        avg_rating = sum(f.rating for f in feedbacks) / total
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for f in feedbacks:
            dist[f.rating] = dist.get(f.rating, 0) + 1

        return FeedbackSummary(
            article=article,
            marketplace=self.marketplace,
            total_reviews=total,
            average_rating=round(avg_rating, 2),
            rating_distribution=dist,
        )

    async def search_competitors(
        self, query: str, limit: int = 10
    ) -> list[ProductCard]:
        """Поиск товаров-конкурентов по запросу (опционально)."""
        raise NotImplementedError
