"""Price and market trends analysis module."""

from decimal import Decimal

from marketplace_assistant.models.product import (
    ProductCard,
    ProductPriceHistory,
)
from marketplace_assistant.utils.logger import get_logger

logger = get_logger(__name__)


class PriceTrendResult:
    """Результат анализа тренда цены."""

    def __init__(
        self,
        article: str,
        marketplace: str,
        current_price: Decimal,
        min_price: Decimal,
        max_price: Decimal,
        avg_price: Decimal,
        trend_direction: str,  # up | down | stable
        price_change_percent: float,
        volatility: float,
        days_analyzed: int,
    ):
        self.article = article
        self.marketplace = marketplace
        self.current_price = current_price
        self.min_price = min_price
        self.max_price = max_price
        self.avg_price = avg_price
        self.trend_direction = trend_direction
        self.price_change_percent = price_change_percent
        self.volatility = volatility
        self.days_analyzed = days_analyzed

    def to_dict(self) -> dict:
        return {
            "article": self.article,
            "marketplace": self.marketplace,
            "current_price": float(self.current_price),
            "min_price": float(self.min_price),
            "max_price": float(self.max_price),
            "avg_price": float(self.avg_price),
            "trend_direction": self.trend_direction,
            "price_change_percent": round(self.price_change_percent, 2),
            "volatility": round(self.volatility, 4),
            "days_analyzed": self.days_analyzed,
        }


async def analyze_price_trend(
    price_history: ProductPriceHistory,
    current_price: Decimal | None = None,
) -> PriceTrendResult:
    """Анализ тренда цены на основе истории.

    Args:
        price_history: История цен.
        current_price: Текущая цена (если None — берётся последняя запись).

    Returns:
        PriceTrendResult с анализом тренда.
    """
    records = price_history.records
    if not records:
        return PriceTrendResult(
            article=price_history.article,
            marketplace=price_history.marketplace,
            current_price=current_price or Decimal("0"),
            min_price=Decimal("0"),
            max_price=Decimal("0"),
            avg_price=Decimal("0"),
            trend_direction="stable",
            price_change_percent=0.0,
            volatility=0.0,
            days_analyzed=0,
        )

    prices = []
    for r in records:
        price = r.get("price")
        if isinstance(price, Decimal):
            prices.append(price)
        elif isinstance(price, (int, float)):
            prices.append(Decimal(str(price)))

    if not prices:
        return PriceTrendResult(
            article=price_history.article,
            marketplace=price_history.marketplace,
            current_price=current_price or Decimal("0"),
            min_price=Decimal("0"),
            max_price=Decimal("0"),
            avg_price=Decimal("0"),
            trend_direction="stable",
            price_change_percent=0.0,
            volatility=0.0,
            days_analyzed=0,
        )

    current = current_price or prices[-1]
    first_price = prices[0]
    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)

    # Изменение цены в процентах
    if first_price > 0:
        change_percent = float((current - first_price) / first_price * 100)
    else:
        change_percent = 0.0

    # Определение направления тренда
    if change_percent > 3:
        trend = "up"
    elif change_percent < -3:
        trend = "down"
    else:
        trend = "stable"

    # Волатильность (среднеквадратичное отклонение / средняя)
    if avg_price > 0:
        variance = sum(float((p - avg_price) ** 2) for p in prices) / len(prices)
        volatility = (variance ** 0.5) / float(avg_price)
    else:
        volatility = 0.0

    return PriceTrendResult(
        article=price_history.article,
        marketplace=price_history.marketplace,
        current_price=current,
        min_price=min_price,
        max_price=max_price,
        avg_price=avg_price,
        trend_direction=trend,
        price_change_percent=change_percent,
        volatility=volatility,
        days_analyzed=len(records),
    )


async def compare_competitors(
    main_product: ProductCard,
    competitors: list[ProductCard],
) -> dict:
    """Сравнить основной товар с конкурентами.

    Args:
        main_product: Основной товар.
        competitors: Список товаров конкурентов.

    Returns:
        Словарь со сравнением.
    """
    if not competitors:
        return {
            "main_product": main_product.name,
            "competitors_count": 0,
            "position_by_price": None,
            "position_by_rating": None,
            "average_competitor_price": None,
        }

    comp_prices = [
        float(c.price) for c in competitors if c.price and c.price > 0
    ]
    comp_ratings = [
        c.rating for c in competitors if c.rating and c.rating > 0
    ]

    # Позиция по цене
    main_price = float(main_product.price) if main_product.price else 0
    all_prices = sorted(comp_prices + [main_price])
    price_position = (
        all_prices.index(main_price) + 1 if main_price in all_prices else None
    )

    # Позиция по рейтингу
    main_rating = main_product.rating or 0
    all_ratings = sorted(
        comp_ratings + [main_rating], reverse=True
    )
    rating_position = (
        all_ratings.index(main_rating) + 1 if main_rating in all_ratings else None
    )

    avg_comp_price = (
        sum(comp_prices) / len(comp_prices) if comp_prices else None
    )

    return {
        "main_product": main_product.name,
        "competitors_count": len(competitors),
        "position_by_price": price_position,
        "position_by_rating": rating_position,
        "average_competitor_price": round(avg_comp_price, 2) if avg_comp_price else None,
        "is_cheaper_than_average": (
            main_price < avg_comp_price if avg_comp_price else None
        ),
    }


async def get_market_insights(
    main_product: ProductCard,
    competitors: list[ProductCard],
    feedback_summary: object | None = None,
) -> dict:
    """Получить общую аналитику по рынку и позиции товара."""
    competitor_analysis = await compare_competitors(main_product, competitors)

    return {
        "product": main_product.model_dump(mode="json"),
        "competitor_analysis": competitor_analysis,
        "price_recommendation": _generate_price_recommendation(
            main_product, competitor_analysis
        ),
    }


def _generate_price_recommendation(
    product: ProductCard, analysis: dict
) -> str | None:
    """Сгенерировать рекомендацию по цене на основе конкурентного анализа."""
    avg_price = analysis.get("average_competitor_price")
    if avg_price is None or not product.price:
        return None

    main_price = float(product.price)
    diff_pct = ((main_price - avg_price) / avg_price) * 100

    if diff_pct > 20:
        return (
            f"⚠️ Цена выше средней по рынку на {diff_pct:.0f}%. "
            f"Рекомендуется снизить цену для повышения конкурентоспособности."
        )
    elif diff_pct < -20:
        return (
            f"💰 Цена ниже средней на {abs(diff_pct):.0f}%. "
            f"Возможен рост цены для увеличения маржи."
        )
    elif abs(diff_pct) <= 5:
        return (
            "✅ Цена оптимальна — близка к средней рыночной."
        )
    return None
