"""Fixtures for marketplace assistant tests."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from marketplace_assistant.models.feedback import Feedback, SentimentResult
from marketplace_assistant.models.product import ProductCard, ProductPriceHistory


@pytest.fixture
def sample_product_card() -> ProductCard:
    """Базовая карточка товара для тестов."""
    return ProductCard(
        marketplace="wb",
        article="12345678",
        name="Тестовый товар",
        brand="TestBrand",
        category="Электроника",
        price=Decimal("1999.00"),
        old_price=Decimal("2499.00"),
        rating=4.3,
        reviews_count=127,
        stock=50,
        image_url="https://test.ru/img.jpg",
        description="Тестовое описание товара.",
        characteristics={"Цвет": "Чёрный", "Размер": "M"},
    )


@pytest.fixture
def sample_ozon_product_card() -> ProductCard:
    """Карточка товара Ozon для тестов."""
    return ProductCard(
        marketplace="ozon",
        article="98765432",
        name="Тестовый товар Ozon",
        brand="OzonBrand",
        category="Косметика",
        price=Decimal("1299.00"),
        rating=4.5,
        reviews_count=89,
        stock=30,
    )


@pytest.fixture
def sample_feedbacks() -> list[Feedback]:
    """Список тестовых отзывов."""
    return [
        Feedback(
            id="fb-1",
            marketplace="wb",
            article="12345678",
            text="Отличный товар, качество на высоте! Рекомендую всем.",
            rating=5,
            author="Иван",
            pros="Качество, доставка",
            likes=12,
        ),
        Feedback(
            id="fb-2",
            marketplace="wb",
            article="12345678",
            text="Нормально, но цена завышена. Ожидал большего за такие деньги.",
            rating=3,
            author="Мария",
            cons="Цена",
            likes=5,
        ),
        Feedback(
            id="fb-3",
            marketplace="wb",
            article="12345678",
            text="Ужасное качество, сломался через неделю. Оформляю возврат.",
            rating=1,
            author="Пётр",
            cons="Качество, брак",
            likes=8,
        ),
        Feedback(
            id="fb-4",
            marketplace="wb",
            article="12345678",
            text="Хороший товар за свою цену. Доставка быстрая, упаковка отличная.",
            rating=4,
            author="Анна",
            pros="Цена, доставка, упаковка",
            likes=3,
        ),
        Feedback(
            id="fb-5",
            marketplace="wb",
            article="12345678",
            text="Не подошёл по размеру, хотя в описании указано верно.",
            rating=2,
            author="Сергей",
            cons="Размер",
            likes=2,
        ),
    ]


@pytest.fixture
def sample_price_history() -> ProductPriceHistory:
    """История цены для тестов."""
    return ProductPriceHistory(
        article="12345678",
        marketplace="wb",
        records=[
            {"date": "2025-01-01", "price": Decimal("2500"), "discount": 10},
            {"date": "2025-01-08", "price": Decimal("2400"), "discount": 15},
            {"date": "2025-01-15", "price": Decimal("2300"), "discount": 20},
            {"date": "2025-01-22", "price": Decimal("2200"), "discount": 25},
            {"date": "2025-01-29", "price": Decimal("1999"), "discount": 30},
        ],
    )


@pytest.fixture
def sample_sentiment_results() -> list[SentimentResult]:
    """Результаты тонального анализа."""
    return [
        SentimentResult(
            text_hash="hash1",
            sentiment="positive",
            score=0.8,
            keywords=["отличный", "качество"],
            language="ru",
        ),
        SentimentResult(
            text_hash="hash2",
            sentiment="neutral",
            score=0.0,
            keywords=[],
            language="ru",
        ),
        SentimentResult(
            text_hash="hash3",
            sentiment="negative",
            score=-0.6,
            keywords=["ужасное", "качество", "сломался"],
            language="ru",
        ),
    ]


@pytest.fixture
def sample_competitors() -> list[ProductCard]:
    """Список товаров-конкурентов для тестов."""
    return [
        ProductCard(
            marketplace="wb",
            article="comp-1",
            name="Конкурент 1",
            brand="BrandA",
            price=Decimal("1800.00"),
            rating=4.0,
            reviews_count=200,
        ),
        ProductCard(
            marketplace="wb",
            article="comp-2",
            name="Конкурент 2",
            brand="BrandB",
            price=Decimal("2200.00"),
            rating=4.5,
            reviews_count=150,
        ),
        ProductCard(
            marketplace="wb",
            article="comp-3",
            name="Конкурент 3",
            brand="BrandC",
            price=Decimal("2500.00"),
            rating=3.8,
            reviews_count=80,
        ),
    ]


@pytest.fixture
def mock_wb_parser():
    """Мок-парсер Wildberries с предсказуемыми данными."""
    from marketplace_assistant.parsers.wildberries import WildberriesParser

    parser = WildberriesParser(mock_mode=True)

    # Можно замокать конкретные методы при необходимости
    return parser


@pytest.fixture
def mock_ozon_parser():
    """Мок-парсер Ozon с предсказуемыми данными."""
    from marketplace_assistant.parsers.ozon import OzonParser

    parser = OzonParser(mock_mode=True)
    return parser


@pytest_asyncio.fixture
async def mock_http_client():
    """Асинхронный HTTP-клиент с замоканными ответами."""
    with patch("httpx.AsyncClient") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_llm_analytics():
    """Мок LLM-аналитики."""
    from marketplace_assistant.analytics.llm_analytics import LLMAnalytics

    llm = LLMAnalytics(mock_mode=True)
    return llm
