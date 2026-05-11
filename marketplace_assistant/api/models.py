"""Pydantic models for API request/response validation."""


from pydantic import BaseModel, Field


class ProductCardResponse(BaseModel):
    """Ответ с карточкой товара."""

    marketplace: str
    article: str
    name: str
    brand: str | None = None
    category: str | None = None
    price: float = 0.0
    old_price: float | None = None
    rating: float | None = None
    reviews_count: int = 0
    stock: int = 0
    image_url: str | None = None
    description: str | None = None
    characteristics: dict = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    """Ответ с одним отзывом."""

    id: str
    rating: int
    text: str
    author: str | None = None
    date: str | None = None
    pros: str | None = None
    cons: str | None = None
    likes: int = 0


class FeedbackSummaryResponse(BaseModel):
    """Ответ с суммаризацией отзывов."""

    article: str
    marketplace: str
    total_reviews: int
    average_rating: float
    rating_distribution: dict[int, int]
    top_positive_themes: list[str]
    top_complaints: list[str]
    overall_sentiment: str
    summary_short: str | None = None


class PriceTrendResponse(BaseModel):
    """Ответ с анализом тренда цены."""

    article: str
    marketplace: str
    current_price: float
    min_price: float
    max_price: float
    avg_price: float
    trend_direction: str
    price_change_percent: float
    days_analyzed: int


class CompetitorResponse(BaseModel):
    """Ответ с информацией о конкуренте."""

    article: str
    name: str
    price: float
    rating: float | None = None
    reviews_count: int = 0
    marketplace: str
    url: str | None = None


class CompetitorAnalysisResponse(BaseModel):
    """Ответ с анализом конкурентов."""

    main_product: str
    competitors_count: int
    position_by_price: int | None = None
    position_by_rating: int | None = None
    average_competitor_price: float | None = None
    is_cheaper_than_average: bool | None = None


class ErrorResponse(BaseModel):
    """Стандартный ответ с ошибкой."""

    error: str
    detail: str | None = None
    status_code: int = 400


class HealthResponse(BaseModel):
    """Ответ health check."""

    status: str = "ok"
    version: str = "0.2.0"
    mock_mode: bool = True
