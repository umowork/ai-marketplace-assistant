"""Feedback and review domain models."""

from datetime import datetime

from pydantic import BaseModel, Field


class Feedback(BaseModel):
    """Одиночный отзыв о товаре."""

    id: str = Field(..., description="ID отзыва")
    marketplace: str = Field(..., description="Маркетплейс")
    article: str = Field(..., description="Артикул товара")
    text: str = Field(..., description="Текст отзыва")
    rating: int = Field(..., ge=1, le=5, description="Оценка от 1 до 5")
    author: str | None = Field(None, description="Имя автора")
    date: datetime | None = Field(None, description="Дата отзыва")
    pros: str | None = Field(None, description="Достоинства")
    cons: str | None = Field(None, description="Недостатки")
    likes: int = Field(0, description="Количество лайков")


class FeedbackSummary(BaseModel):
    """Обобщённая аналитика по отзывам."""

    article: str
    marketplace: str
    total_reviews: int
    average_rating: float = Field(..., ge=0, le=5)
    rating_distribution: dict[int, int] = Field(
        default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    )
    top_positive_themes: list[str] = Field(default_factory=list)
    top_complaints: list[str] = Field(default_factory=list)
    overall_sentiment: str = Field(default="neutral", description="positive/negative/neutral")
    summary_short: str | None = Field(None, description="Краткая сводка на 1-2 предложения")


class SentimentResult(BaseModel):
    """Результат тонального анализа текста."""

    text_hash: str = Field(..., description="Хеш текста")
    sentiment: str = Field(..., description="positive/negative/neutral")
    score: float = Field(..., ge=-1.0, le=1.0, description="Тональная оценка от -1 до 1")
    keywords: list[str] = Field(default_factory=list, description="Ключевые слова")
    language: str = Field("ru", description="Язык текста")
