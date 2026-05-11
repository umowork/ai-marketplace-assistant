"""Tests for FastAPI application."""

import pytest
from httpx import ASGITransport, AsyncClient

from marketplace_assistant.api.fastapi_app import create_app


@pytest.fixture
def app():
    """FastAPI приложение для тестов (mock_mode=True)."""
    return create_app(mock_mode=True)


@pytest.fixture
async def client(app):
    """Async HTTP клиент для тестов."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealth:
    """Тесты health check."""

    @pytest.mark.asyncio
    async def test_health_ok(self, client):
        """Проверка GET /health."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.2.0"
        assert data["mock_mode"] is True


class TestProductEndpoint:
    """Тесты /product endpoint."""

    @pytest.mark.asyncio
    async def test_get_product_wb(self, client):
        """Проверка получения товара WB."""
        resp = await client.get("/product", params={"article": "12345678", "marketplace": "wb"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["marketplace"] == "wb"
        assert data["article"] == "12345678"
        assert "name" in data
        assert data["price"] > 0

    @pytest.mark.asyncio
    async def test_get_product_ozon(self, client):
        """Проверка получения товара Ozon."""
        resp = await client.get("/product", params={"article": "98765432", "marketplace": "ozon"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["marketplace"] == "ozon"
        assert data["article"] == "98765432"

    @pytest.mark.asyncio
    async def test_get_product_invalid_article(self, client, app):
        """Проверка обработки неверного артикула."""
        # Создаём приложение без mock_mode для теста ошибки

        resp = await client.get("/product", params={"article": "abc", "marketplace": "wb"})
        assert resp.status_code == 404


class TestFeedbacksEndpoint:
    """Тесты /feedbacks endpoint."""

    @pytest.mark.asyncio
    async def test_get_feedbacks(self, client):
        """Проверка получения отзывов."""
        resp = await client.get(
            "/feedbacks",
            params={"article": "12345678", "marketplace": "wb", "limit": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "rating" in data[0]
            assert "text" in data[0]

    @pytest.mark.asyncio
    async def test_get_feedbacks_ozon(self, client):
        """Проверка получения отзывов Ozon."""
        resp = await client.get(
            "/feedbacks",
            params={"article": "98765432", "marketplace": "ozon", "limit": 5},
        )
        assert resp.status_code == 200


class TestAnalyzeFeedbacksEndpoint:
    """Тесты /analyze-feedbacks endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_feedbacks(self, client):
        """Проверка анализа отзывов."""
        resp = await client.get(
            "/analyze-feedbacks",
            params={"article": "12345678", "marketplace": "wb"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "article" in data
        assert "average_rating" in data
        assert "overall_sentiment" in data
        assert "top_positive_themes" in data
        assert "top_complaints" in data


class TestPriceTrendEndpoint:
    """Тесты /price-trend endpoint."""

    @pytest.mark.asyncio
    async def test_price_trend(self, client):
        """Проверка анализа тренда цены."""
        resp = await client.get(
            "/price-trend",
            params={"article": "12345678", "marketplace": "wb", "days": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "current_price" in data
        assert "trend_direction" in data
        assert "price_change_percent" in data


class TestCompetitorsEndpoint:
    """Тесты /competitors endpoint."""

    @pytest.mark.asyncio
    async def test_competitors(self, client):
        """Проверка анализа конкурентов."""
        resp = await client.get(
            "/competitors",
            params={"query": "наушники", "marketplace": "wb"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "competitors_count" in data
        assert data["competitors_count"] > 0


class TestGenerateDescriptionEndpoint:
    """Тесты /generate-description endpoint."""

    @pytest.mark.asyncio
    async def test_generate_description(self, client):
        """Проверка генерации описания."""
        resp = await client.post(
            "/generate-description",
            params={
                "product_name": "Наушники",
                "features": "bluetooth,беспроводные",
                "marketplace": "wb",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "description" in data
        assert len(data["description"]) > 0


class TestMarketInsightsEndpoint:
    """Тесты /market-insights endpoint."""

    @pytest.mark.asyncio
    async def test_market_insights(self, client):
        """Проверка комплексной аналитики."""
        resp = await client.get(
            "/market-insights",
            params={"article": "12345678", "marketplace": "wb"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "product" in data
        assert "feedbacks_summary" in data
        assert "price_trend" in data
        assert "competitors" in data
