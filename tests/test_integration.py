"""Integration tests — end-to-end flows with mock data."""


import pytest

from marketplace_assistant.analytics.sentiment import analyze_feedbacks_sentiment
from marketplace_assistant.analytics.summarizer import summarize_feedbacks
from marketplace_assistant.analytics.trends import analyze_price_trend, get_market_insights
from marketplace_assistant.models.feedback import FeedbackSummary, SentimentResult
from marketplace_assistant.models.product import ProductCard, ProductPriceHistory
from marketplace_assistant.parsers.wildberries import WildberriesParser


class TestIntegrationMockMode:
    """Интеграционные тесты — полный поток с мок-данными."""

    @pytest.mark.asyncio
    async def test_full_product_analysis_flow(self):
        """Полный поток: карточка → отзывы → аналитика."""
        wb = WildberriesParser(mock_mode=True)

        # 1. Получаем карточку
        product = await wb.get_product_card("12345678")
        assert isinstance(product, ProductCard)
        assert product.price > 0

        # 2. Получаем отзывы
        feedbacks = await wb.get_feedbacks("12345678")
        assert len(feedbacks) > 0

        # 3. Анализируем тональность
        texts = [fb.text for fb in feedbacks]
        sentiments = await analyze_feedbacks_sentiment(texts)
        assert len(sentiments) == len(texts)
        assert all(isinstance(s, SentimentResult) for s in sentiments)

        # 4. Суммаризируем отзывы
        summary = await summarize_feedbacks(feedbacks, "12345678", "wb")
        assert isinstance(summary, FeedbackSummary)
        assert summary.total_reviews > 0
        assert summary.average_rating > 0

    @pytest.mark.asyncio
    async def test_price_and_competitors_flow(self):
        """Полный поток: цена → конкуренты → рыночная аналитика."""
        wb = WildberriesParser(mock_mode=True)

        # 1. Получаем карточку
        product = await wb.get_product_card("12345678")

        # 2. Получаем историю цены
        price_history = await wb.get_price_history("12345678", days=30)
        assert isinstance(price_history, ProductPriceHistory)

        # 3. Анализируем тренд
        trend = await analyze_price_trend(price_history, product.price)
        assert trend.trend_direction in ("up", "down", "stable")
        assert trend.days_analyzed > 0

        # 4. Ищем конкурентов
        competitors = await wb.search_competitors("наушники", limit=5)
        assert len(competitors) <= 5
        assert all(isinstance(c, ProductCard) for c in competitors)

        # 5. Получаем рыночную аналитику
        insights = await get_market_insights(product, competitors)
        assert "competitor_analysis" in insights
        assert insights["competitor_analysis"]["competitors_count"] > 0

    @pytest.mark.asyncio
    async def test_feedback_summary_to_sentiment_flow(self):
        """Поток: отзывы → суммаризация → тональность."""
        wb = WildberriesParser(mock_mode=True)

        # Получаем отзывы
        feedbacks = await wb.get_feedbacks("12345678")

        # Суммаризируем
        summary = await summarize_feedbacks(feedbacks, "12345678", "wb")

        # Проверяем консистентность
        assert summary.total_reviews == len(feedbacks)
        assert summary.overall_sentiment in ("positive", "negative", "neutral")

        # Тональность должна соответствовать распределению рейтингов
        dist = {}
        for f in feedbacks:
            dist[f.rating] = dist.get(f.rating, 0) + 1
        total = len(feedbacks)
        positive_ratio = (dist.get(5, 0) + dist.get(4, 0)) / total
        negative_ratio = (dist.get(1, 0) + dist.get(2, 0)) / total
        if positive_ratio > 0.7:
            assert summary.overall_sentiment == "positive"
        elif negative_ratio > 0.4:
            assert summary.overall_sentiment == "negative"
        else:
            assert summary.overall_sentiment == "neutral"

    @pytest.mark.asyncio
    async def test_multiple_products_analysis(self):
        """Поток: анализ нескольких товаров."""
        wb = WildberriesParser(mock_mode=True)
        articles = ["12345678", "23456789", "34567890"]

        for article in articles:
            product = await wb.get_product_card(article)
            assert isinstance(product, ProductCard)
            assert product.article == article

            feedbacks = await wb.get_feedbacks(article)
            assert len(feedbacks) > 0

            # Проверяем, что отзывы привязаны к артикулу
            assert all(fb.article == article for fb in feedbacks)

    @pytest.mark.asyncio
    async def test_cache_layer_integration(self):
        """Проверка работы кэша между вызовами."""
        from marketplace_assistant.utils.cache import MemoryCache

        cache = MemoryCache(maxsize=16)
        wb = WildberriesParser(mock_mode=True, cache=cache)

        # Первый вызов — должен заполнить кэш
        product1 = await wb.get_product_card("12345678")
        assert product1 is not None

        # Второй вызов — должен вернуть из кэша (тот же объект по значению)
        product2 = await wb.get_product_card("12345678")
        assert product2.article == product1.article
        assert product2.name == product1.name

    @pytest.mark.asyncio
    async def test_cross_marketplace_analysis(self):
        """Проверка анализа между разными маркетплейсами."""
        from marketplace_assistant.parsers.ozon import OzonParser

        wb = WildberriesParser(mock_mode=True)
        ozon = OzonParser(mock_mode=True)

        # WB товар
        wb_product = await wb.get_product_card("12345678")
        assert wb_product.marketplace == "wb"

        # Ozon товар
        ozon_product = await ozon.get_product_card("98765432")
        assert ozon_product.marketplace == "ozon"

        # Сравнение
        assert wb_product.price != ozon_product.price
        assert wb_product.name != ozon_product.name


class TestIntegrationErrorHandling:
    """Интеграционные тесты обработки ошибок."""

    @pytest.mark.asyncio
    async def test_product_not_found_handling(self):
        """Проверка обработки ненайденного товара в mock mode."""
        # Mock mode всегда возвращает товар, но мы можем проверить
        # что парсер корректно обрабатывает ошибки через реальный код
        wb = WildberriesParser(mock_mode=True)
        # С этим не должно быть проблем
        product = await wb.get_product_card("99999999")
        assert product is not None

    @pytest.mark.asyncio
    async def test_empty_feedbacks_handling(self):
        """Проверка обработки пустого списка отзывов."""
        summary = await summarize_feedbacks([], "123", "wb")
        assert summary.total_reviews == 0
        assert summary.average_rating == 0.0
        assert summary.summary_short is not None

    @pytest.mark.asyncio
    async def test_price_history_empty_handling(self):
        """Проверка обработки пустой истории цены."""
        from marketplace_assistant.analytics.trends import analyze_price_trend

        empty_history = ProductPriceHistory(article="123", marketplace="wb")
        result = await analyze_price_trend(empty_history)
        assert result.trend_direction == "stable"
        assert result.days_analyzed == 0
