"""Tests for analytics modules — sentiment, summarizer, trends, LLM."""

import pytest

from marketplace_assistant.analytics.sentiment import analyze_feedbacks_sentiment, analyze_sentiment
from marketplace_assistant.analytics.summarizer import summarize_feedbacks
from marketplace_assistant.analytics.trends import (
    PriceTrendResult,
    analyze_price_trend,
    compare_competitors,
    get_market_insights,
)
from marketplace_assistant.models.feedback import SentimentResult


class TestSentimentAnalysis:
    """Тесты тонального анализа."""

    @pytest.mark.asyncio
    async def test_sentiment_positive(self):
        """Проверка определения позитивной тональности."""
        result = await analyze_sentiment("Отличный товар, качество на высоте!")
        assert isinstance(result, SentimentResult)
        assert result.sentiment == "positive"
        assert result.score > 0

    @pytest.mark.asyncio
    async def test_sentiment_negative(self):
        """Проверка определения негативной тональности."""
        result = await analyze_sentiment("Ужасное качество, сломался через неделю")
        assert result.sentiment == "negative"
        assert result.score < 0

    @pytest.mark.asyncio
    async def test_sentiment_neutral(self):
        """Проверка нейтральной тональности."""
        result = await analyze_sentiment("Купил товар, доставили вовремя")
        assert result.sentiment in ("neutral", "positive")

    @pytest.mark.asyncio
    async def test_sentiment_empty_text(self):
        """Проверка обработки пустого текста."""
        result = await analyze_sentiment("")
        assert result.sentiment == "neutral"
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_sentiment_batch(self):
        """Проверка пакетного анализа."""
        texts = [
            "Отличный товар!",
            "Ужасный брак!",
            "Обычный товар, без нареканий",
        ]
        results = await analyze_feedbacks_sentiment(texts)
        assert len(results) == 3
        assert results[0].sentiment == "positive"
        assert results[1].sentiment == "negative"

    @pytest.mark.asyncio
    async def test_sentiment_with_llm_fallback(self, mock_llm_analytics):
        """Проверка тонального анализа с LLM fallback."""
        result = await analyze_sentiment(
            "Хороший товар, рекомендую",
            llm_analytics=mock_llm_analytics,
        )
        assert isinstance(result, SentimentResult)
        assert result.sentiment in ("positive", "neutral")


class TestFeedbackSummarizer:
    """Тесты суммаризации отзывов."""

    @pytest.mark.asyncio
    async def test_summarize_empty(self):
        """Проверка суммаризации пустого списка."""
        summary = await summarize_feedbacks([], "123", "wb")
        assert summary.total_reviews == 0
        assert summary.average_rating == 0.0

    @pytest.mark.asyncio
    async def test_summarize_with_feedbacks(self, sample_feedbacks):
        """Проверка суммаризации с отзывами."""
        summary = await summarize_feedbacks(sample_feedbacks, "12345678", "wb")
        assert summary.total_reviews == 5
        assert summary.average_rating > 0
        assert summary.rating_distribution[5] == 1
        assert summary.rating_distribution[1] == 1
        assert len(summary.top_positive_themes) > 0
        assert len(summary.top_complaints) > 0
        assert summary.overall_sentiment in ("positive", "neutral", "negative")

    @pytest.mark.asyncio
    async def test_summarize_rating_distribution(self, sample_feedbacks):
        """Проверка распределения оценок."""
        summary = await summarize_feedbacks(sample_feedbacks, "12345678", "wb")
        dist = summary.rating_distribution
        assert sum(dist.values()) == 5
        assert dist[5] == 1
        assert dist[3] == 1
        assert dist[1] == 1

    @pytest.mark.asyncio
    async def test_summarize_generates_short_summary(self, sample_feedbacks):
        """Проверка генерации краткой сводки."""
        summary = await summarize_feedbacks(sample_feedbacks, "12345678", "wb")
        assert summary.summary_short is not None
        short = summary.summary_short.lower()
        assert "средняя оценка" in summary.summary_short or "средняя" in short
        assert len(summary.summary_short) > 10


class TestPriceTrends:
    """Тесты анализа трендов цены."""

    @pytest.mark.asyncio
    async def test_analyze_price_trend_down(self, sample_price_history):
        """Проверка определения нисходящего тренда."""
        result = await analyze_price_trend(sample_price_history)
        assert isinstance(result, PriceTrendResult)
        assert result.article == "12345678"
        assert result.trend_direction == "down"
        assert result.price_change_percent < 0
        assert result.days_analyzed == 5

    @pytest.mark.asyncio
    async def test_analyze_price_trend_empty(self):
        """Проверка анализа пустой истории."""
        from marketplace_assistant.models.product import ProductPriceHistory

        empty = ProductPriceHistory(article="123", marketplace="wb")
        result = await analyze_price_trend(empty)
        assert result.trend_direction == "stable"
        assert result.days_analyzed == 0

    @pytest.mark.asyncio
    async def test_analyze_price_trend_with_current_price(self, sample_price_history):
        """Проверка анализа с указанием текущей цены."""
        from decimal import Decimal

        result = await analyze_price_trend(sample_price_history, current_price=Decimal("1800"))
        assert result.current_price == Decimal("1800")
        assert result.price_change_percent < 0

    @pytest.mark.asyncio
    async def test_compare_competitors(
        self, sample_product_card, sample_competitors
    ):
        """Проверка сравнения с конкурентами."""
        analysis = await compare_competitors(sample_product_card, sample_competitors)
        assert analysis["competitors_count"] == 3
        assert analysis["position_by_price"] is not None
        assert analysis["position_by_rating"] is not None

    @pytest.mark.asyncio
    async def test_compare_competitors_empty(self, sample_product_card):
        """Проверка сравнения без конкурентов."""
        analysis = await compare_competitors(sample_product_card, [])
        assert analysis["competitors_count"] == 0
        assert analysis["position_by_price"] is None

    @pytest.mark.asyncio
    async def test_get_market_insights(
        self, sample_product_card, sample_competitors, sample_feedbacks
    ):
        """Проверка получения общей аналитики."""
        from marketplace_assistant.analytics.summarizer import summarize_feedbacks

        fb_summary = await summarize_feedbacks(sample_feedbacks, "12345678", "wb")
        insights = await get_market_insights(
            sample_product_card, sample_competitors, fb_summary
        )
        assert "product" in insights
        assert "competitor_analysis" in insights
        assert "price_recommendation" in insights


class TestLLMAnalytics:
    """Тесты LLM-аналитики (mock mode)."""

    @pytest.mark.asyncio
    async def test_analyze_sentiment_mock(self, mock_llm_analytics):
        """Проверка тонального анализа через LLM в mock mode."""
        result = await mock_llm_analytics.analyze_sentiment("Отличный товар!")
        assert isinstance(result, SentimentResult)
        assert result.sentiment == "positive"
        assert result.score >= 0.5

    @pytest.mark.asyncio
    async def test_analyze_sentiment_mock_negative(self, mock_llm_analytics):
        """Проверка негативной тональности в mock mode."""
        result = await mock_llm_analytics.analyze_sentiment("Плохой товар")
        assert result.sentiment == "neutral"

    @pytest.mark.asyncio
    async def test_generate_description_mock(self, mock_llm_analytics):
        """Проверка генерации описания в mock mode."""
        desc = await mock_llm_analytics.generate_description(
            "Наушники", ["беспроводные", "bluetooth"], "wb"
        )
        assert isinstance(desc, str)
        assert "Наушники" in desc
        assert len(desc) > 50

    @pytest.mark.asyncio
    async def test_improve_card_mock(self, mock_llm_analytics):
        """Проверка улучшения карточки в mock mode."""
        card = {"name": "Тестовый товар", "price": "1000"}
        improved = await mock_llm_analytics.improve_card(card, "wb")
        assert "improved_name" in improved
        assert "improved_description" in improved
        assert "suggestions" in improved

    @pytest.mark.asyncio
    async def test_summarize_feedbacks_llm_mock(self, mock_llm_analytics, sample_feedbacks):
        """Проверка суммаризации отзывов через LLM в mock mode."""
        summary = await mock_llm_analytics.summarize_feedbacks_llm(
            sample_feedbacks, "12345678", "wb"
        )
        assert summary.total_reviews == 5
        assert summary.average_rating > 0
        assert summary.summary_short is not None
