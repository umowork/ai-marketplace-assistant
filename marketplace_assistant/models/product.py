"""Product domain models."""

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ProductCard(BaseModel):
    """Модель карточки товара с маркетплейса."""

    marketplace: str = Field(..., description="Маркетплейс: wb или ozon")
    article: str = Field(..., description="Артикул товара")
    name: str = Field(..., description="Название товара")
    brand: str | None = Field(None, description="Бренд")
    category: str | None = Field(None, description="Категория")
    price: Decimal = Field(..., ge=0, description="Текущая цена в рублях")
    old_price: Decimal | None = Field(None, ge=0, description="Цена до скидки")
    rating: float | None = Field(None, ge=0, le=5, description="Рейтинг товара")
    reviews_count: int = Field(0, ge=0, description="Количество отзывов")
    stock: int = Field(0, ge=0, description="Остаток на складе")
    image_url: str | None = Field(None, description="URL изображения")
    description: str | None = Field(None, description="Описание товара")
    characteristics: dict[str, str] = Field(default_factory=dict, description="Характеристики")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("price")
    @classmethod
    def price_not_zero(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class ProductPriceHistory(BaseModel):
    """История изменения цены товара."""

    article: str
    marketplace: str
    records: list[dict] = Field(default_factory=list, description="Список {date, price, discount}")


class CompetitorOffer(BaseModel):
    """Товар конкурента для сравнения."""

    article: str
    name: str
    price: Decimal
    rating: float | None = None
    reviews_count: int = 0
    marketplace: str
    url: str | None = None
