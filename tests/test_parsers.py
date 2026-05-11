"""Tests for Wildberries and Ozon parsers."""

from decimal import Decimal

import pytest

from marketplace_assistant.models.product import ProductCard
from marketplace_assistant.parsers.errors import ParseError, ProductNotFoundError
from marketplace_assistant.parsers.wildberries import (
    _get_wb_subject,
    _get_wb_volume_parts,
    _parse_wb_article,
)


class TestWildberriesParser:
    """Тесты парсера Wildberries (mock mode)."""

    @pytest.mark.asyncio
    async def test_get_product_card_mock(self, mock_wb_parser):
        """Проверка получения карточки товара в mock mode."""
        product = await mock_wb_parser.get_product_card("12345678")
        assert isinstance(product, ProductCard)
        assert product.marketplace == "wb"
        assert product.article == "12345678"
        assert product.name == "Mock Товар WB"
        assert product.price == Decimal("1999.00")
        assert product.rating == 4.3
        assert product.reviews_count == 127

    @pytest.mark.asyncio
    async def test_get_feedbacks_mock(self, mock_wb_parser):
        """Проверка получения отзывов в mock mode."""
        feedbacks = await mock_wb_parser.get_feedbacks("12345678")
        assert len(feedbacks) == 2
        assert feedbacks[0].marketplace == "wb"
        assert feedbacks[0].rating == 5
        assert feedbacks[1].rating == 3

    @pytest.mark.asyncio
    async def test_get_price_history_mock(self, mock_wb_parser):
        """Проверка истории цены в mock mode."""
        history = await mock_wb_parser.get_price_history("12345678", days=10)
        assert history.article == "12345678"
        assert history.marketplace == "wb"
        assert len(history.records) == 10

    @pytest.mark.asyncio
    async def test_search_competitors_mock(self, mock_wb_parser):
        """Проверка поиска конкурентов в mock mode."""
        competitors = await mock_wb_parser.search_competitors("наушники", limit=5)
        assert len(competitors) == 5
        assert all(c.marketplace == "wb" for c in competitors)
        assert all("Конкурент" in c.name for c in competitors)

    @pytest.mark.asyncio
    async def test_get_feedback_summary_mock(self, mock_wb_parser):
        """Проверка базовой суммаризации отзывов через парсер."""
        summary = await mock_wb_parser.get_feedback_summary("12345678")
        assert summary.article == "12345678"
        assert summary.marketplace == "wb"
        assert summary.total_reviews == 2
        assert summary.average_rating == 4.0  # (5 + 3) / 2


class TestOzonParser:
    """Тесты парсера Ozon (mock mode)."""

    @pytest.mark.asyncio
    async def test_get_product_card_mock(self, mock_ozon_parser):
        """Проверка получения карточки товара Ozon в mock mode."""
        product = await mock_ozon_parser.get_product_card("98765432")
        assert isinstance(product, ProductCard)
        assert product.marketplace == "ozon"
        assert product.article == "98765432"
        assert product.name == "Mock Товар Ozon"
        assert product.price == Decimal("1299.00")

    @pytest.mark.asyncio
    async def test_get_feedbacks_mock(self, mock_ozon_parser):
        """Проверка получения отзывов Ozon в mock mode."""
        feedbacks = await mock_ozon_parser.get_feedbacks("98765432")
        assert len(feedbacks) == 2
        assert feedbacks[0].marketplace == "ozon"
        assert feedbacks[0].rating == 4

    @pytest.mark.asyncio
    async def test_get_price_history_mock(self, mock_ozon_parser):
        """Проверка истории цены Ozon в mock mode."""
        history = await mock_ozon_parser.get_price_history("98765432", days=5)
        assert history.marketplace == "ozon"
        assert len(history.records) == 5

    @pytest.mark.asyncio
    async def test_search_competitors_mock(self, mock_ozon_parser):
        """Проверка поиска конкурентов Ozon в mock mode."""
        competitors = await mock_ozon_parser.search_competitors("крем", limit=3)
        assert len(competitors) == 3
        assert all(c.marketplace == "ozon" for c in competitors)


class TestWBParserHelpers:
    """Тесты вспомогательных функций парсера WB."""

    def test_parse_wb_article(self):
        """Проверка парсинга артикула WB."""
        assert _parse_wb_article("12345678") == "12345678"
        assert _parse_wb_article("001234") == "1234"
        with pytest.raises(ParseError):
            _parse_wb_article("abc")

    def test_get_wb_subject(self):
        """Проверка определения subject (волны) для WB."""
        subject = _get_wb_subject("12345678")
        assert isinstance(subject, str)
        assert subject.isdigit()

    def test_get_wb_volume_parts(self):
        """Проверка вычисления vol/part для URL карточки."""
        vol, part = _get_wb_volume_parts("12345678")
        assert vol == 123  # 12345678 // 100000
        assert part == 12345  # 12345678 // 1000


class TestParseErrors:
    """Тесты классов ошибок парсинга."""

    def test_product_not_found_error(self):
        error = ProductNotFoundError("Товар не найден")
        assert str(error) == "Товар не найден"
        assert isinstance(error, Exception)

    def test_parse_error_with_article(self):
        error = ParseError("Некорректный артикул")
        assert str(error) == "Некорректный артикул"
