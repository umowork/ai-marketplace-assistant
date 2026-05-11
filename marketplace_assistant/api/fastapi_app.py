"""FastAPI application — routes for product analysis, feedbacks, competitors."""


from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from marketplace_assistant.analytics.llm_analytics import LLMAnalytics
from marketplace_assistant.analytics.summarizer import summarize_feedbacks
from marketplace_assistant.analytics.trends import (
    analyze_price_trend,
    compare_competitors,
    get_market_insights,
)
from marketplace_assistant.api.models import (
    CompetitorAnalysisResponse,
    ErrorResponse,
    FeedbackResponse,
    FeedbackSummaryResponse,
    HealthResponse,
    PriceTrendResponse,
    ProductCardResponse,
)
from marketplace_assistant.models.product import ProductCard
from marketplace_assistant.parsers.ozon import OzonParser
from marketplace_assistant.parsers.wildberries import WildberriesParser
from marketplace_assistant.utils.cache import create_cache
from marketplace_assistant.utils.logger import get_logger

logger = get_logger(__name__)

# Live instances (lazy init)
_wb_parser: WildberriesParser | None = None
_ozon_parser: OzonParser | None = None
_llm: LLMAnalytics | None = None


def create_app(
    wb_api_key: str = "",
    ozon_client_id: str = "",
    ozon_api_key: str = "",
    llm_api_key: str = "",
    llm_model: str = "gpt-4o-mini",
    llm_provider: str = "openai",
    mock_mode: bool = True,
    redis_url: str | None = None,
) -> FastAPI:
    """Создать и настроить FastAPI приложение."""
    cache = create_cache(redis_url)

    app = FastAPI(
        title="AI Marketplace Assistant API",
        description="API для аналитики товаров на Wildberries и Ozon",
        version="0.2.0",
    )

    # Lazy parsers factory
    def get_wb_parser() -> WildberriesParser:
        global _wb_parser
        if _wb_parser is None:
            _wb_parser = WildberriesParser(
                api_key=wb_api_key,
                mock_mode=mock_mode,
                cache=cache,
            )
        return _wb_parser

    def get_ozon_parser() -> OzonParser:
        global _ozon_parser
        if _ozon_parser is None:
            _ozon_parser = OzonParser(
                client_id=ozon_client_id,
                api_key=ozon_api_key,
                mock_mode=mock_mode,
                cache=cache,
            )
        return _ozon_parser

    def get_llm() -> LLMAnalytics | None:
        global _llm
        if _llm is None and llm_api_key:
            _llm = LLMAnalytics(
                api_key=llm_api_key,
                model=llm_model,
                provider=llm_provider,
                mock_mode=mock_mode,
            )
        return _llm

    # ===== Health =====
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health():
        return HealthResponse(mock_mode=mock_mode)

    # ===== Product =====
    @app.get(
        "/product",
        response_model=ProductCardResponse,
        responses={404: {"model": ErrorResponse}},
        tags=["Product"],
        summary="Получить карточку товара",
    )
    async def get_product(
        article: str = Query(..., description="Артикул товара"),
        marketplace: str = Query("wb", description="Маркетплейс: wb или ozon"),
    ):
        """Получить карточку товара по артикулу."""
        if not article.isdigit():
            raise HTTPException(status_code=404, detail="Invalid article: must be numeric")
        try:
            if marketplace.lower() == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            product = await parser.get_product_card(article)
            return _product_to_response(product)
        except Exception as e:
            logger.error("Error fetching product %s: %s", article, e)
            raise HTTPException(status_code=404, detail=str(e)) from e

    # ===== Feedbacks =====
    @app.get(
        "/feedbacks",
        response_model=list[FeedbackResponse],
        tags=["Feedbacks"],
        summary="Получить отзывы на товар",
    )
    async def get_feedbacks(
        article: str = Query(..., description="Артикул товара"),
        marketplace: str = Query("wb", description="Маркетплейс"),
        limit: int = Query(50, ge=1, le=500, description="Количество отзывов"),
        offset: int = Query(0, ge=0, description="Смещение"),
    ):
        """Получить список отзывов на товар."""
        try:
            if marketplace.lower() == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            feedbacks = await parser.get_feedbacks(article, limit=limit, offset=offset)
            return [
                FeedbackResponse(
                    id=fb.id,
                    rating=fb.rating,
                    text=fb.text[:1000],
                    author=fb.author,
                    date=fb.date.isoformat() if fb.date else None,
                    pros=fb.pros,
                    cons=fb.cons,
                    likes=fb.likes,
                )
                for fb in feedbacks
            ]
        except Exception as e:
            logger.error("Error fetching feedbacks for %s: %s", article, e)
            raise HTTPException(status_code=404, detail=str(e)) from e

    # ===== Analyze Feedbacks =====
    @app.get(
        "/analyze-feedbacks",
        response_model=FeedbackSummaryResponse,
        tags=["Analytics"],
        summary="Анализ отзывов на товар",
    )
    async def analyze_feedbacks(
        article: str = Query(..., description="Артикул товара"),
        marketplace: str = Query("wb", description="Маркетплейс"),
        limit: int = Query(100, ge=1, le=500, description="Количество отзывов для анализа"),
        use_llm: bool = Query(False, description="Использовать LLM для анализа"),
    ):
        """Проанализировать отзывы на товар: тональность, топ-темы, жалобы."""
        try:
            if marketplace.lower() == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            feedbacks = await parser.get_feedbacks(article, limit=limit)
            llm = get_llm() if use_llm else None

            summary = await summarize_feedbacks(
                feedbacks, article, marketplace, llm_analytics=llm
            )
            return FeedbackSummaryResponse(
                article=summary.article,
                marketplace=summary.marketplace,
                total_reviews=summary.total_reviews,
                average_rating=summary.average_rating,
                rating_distribution=summary.rating_distribution,
                top_positive_themes=summary.top_positive_themes,
                top_complaints=summary.top_complaints,
                overall_sentiment=summary.overall_sentiment,
                summary_short=summary.summary_short,
            )
        except Exception as e:
            logger.error("Error analyzing feedbacks for %s: %s", article, e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    # ===== Price Trend =====
    @app.get(
        "/price-trend",
        response_model=PriceTrendResponse,
        tags=["Analytics"],
        summary="Тренд цены товара",
    )
    async def price_trend(
        article: str = Query(..., description="Артикул товара"),
        marketplace: str = Query("wb", description="Маркетплейс"),
        days: int = Query(30, ge=1, le=365, description="Глубина анализа (дни)"),
    ):
        """Получить анализ тренда цены товара."""
        try:
            if marketplace.lower() == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            history = await parser.get_price_history(article, days=days)
            result = await analyze_price_trend(history)
            return PriceTrendResponse(
                article=result.article,
                marketplace=result.marketplace,
                current_price=float(result.current_price),
                min_price=float(result.min_price),
                max_price=float(result.max_price),
                avg_price=float(result.avg_price),
                trend_direction=result.trend_direction,
                price_change_percent=result.price_change_percent,
                days_analyzed=result.days_analyzed,
            )
        except Exception as e:
            logger.error("Error fetching price trend for %s: %s", article, e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    # ===== Competitors =====
    @app.get(
        "/competitors",
        response_model=CompetitorAnalysisResponse,
        tags=["Analytics"],
        summary="Анализ конкурентов по запросу",
    )
    async def competitors(
        query: str = Query(..., description="Поисковый запрос"),
        article: str | None = Query(None, description="Артикул вашего товара для сравнения"),
        marketplace: str = Query("wb", description="Маркетплейс"),
    ):
        """Найти и проанализировать конкурентов по поисковому запросу."""
        try:
            if marketplace.lower() == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            competitors_list = await parser.search_competitors(query, limit=15)

            main_product = None
            if article:
                try:
                    main_product = await parser.get_product_card(article)
                except Exception:
                    logger.warning("Main product %s not found, skipping comparison", article)

            if main_product:
                analysis = await compare_competitors(main_product, competitors_list)
            else:
                analysis = {
                    "main_product": query,
                    "competitors_count": len(competitors_list),
                    "position_by_price": None,
                    "position_by_rating": None,
                    "average_competitor_price": None,
                }

            return CompetitorAnalysisResponse(**analysis)
        except Exception as e:
            logger.error("Error analyzing competitors: %s", e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    # ===== Market Insights =====
    @app.get(
        "/market-insights",
        tags=["Analytics"],
        summary="Полная аналитика по товару",
    )
    async def market_insights(
        article: str = Query(..., description="Артикул товара"),
        marketplace: str = Query("wb", description="Маркетплейс"),
    ):
        """Комплексная аналитика: карточка + отзывы + конкуренты."""
        try:
            if marketplace.lower() == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            # Сбор данных
            product = await parser.get_product_card(article)
            feedbacks = await parser.get_feedbacks(article, limit=50)
            price_history = await parser.get_price_history(article)

            # Аналитика
            summary = await summarize_feedbacks(feedbacks, article, marketplace)
            trend = await analyze_price_trend(price_history, product.price)
            competitors_list = await parser.search_competitors(product.name.split()[0], limit=10)
            market = await get_market_insights(product, competitors_list, summary)

            return {
                "product": _product_to_response(product),
                "feedbacks_summary": FeedbackSummaryResponse(
                    article=summary.article,
                    marketplace=summary.marketplace,
                    total_reviews=summary.total_reviews,
                    average_rating=summary.average_rating,
                    rating_distribution=summary.rating_distribution,
                    top_positive_themes=summary.top_positive_themes,
                    top_complaints=summary.top_complaints,
                    overall_sentiment=summary.overall_sentiment,
                    summary_short=summary.summary_short,
                ).model_dump(),
                "price_trend": PriceTrendResponse(
                    article=trend.article,
                    marketplace=trend.marketplace,
                    current_price=float(trend.current_price),
                    min_price=float(trend.min_price),
                    max_price=float(trend.max_price),
                    avg_price=float(trend.avg_price),
                    trend_direction=trend.trend_direction,
                    price_change_percent=trend.price_change_percent,
                    days_analyzed=trend.days_analyzed,
                ).model_dump(),
                "competitors": market,
            }
        except Exception as e:
            logger.error("Error getting market insights for %s: %s", article, e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    # ===== Generate Description =====
    @app.post(
        "/generate-description",
        tags=["AI"],
        summary="Сгенерировать SEO-описание товара",
    )
    async def generate_description(
        product_name: str = Query(..., description="Название товара"),
        features: str = Query("", description="Характеристики через запятую"),
        marketplace: str = Query("wb", description="Маркетплейс"),
    ):
        """Сгенерировать SEO-описание товара через LLM."""
        try:
            llm = get_llm()
            if not llm:
                # Fallback
                return {
                    "description": (
                        f"✨ {product_name} — лучший выбор!\n\n"
                        f"🔹 Характеристики: {features}\n\n"
                        f"✅ Высокое качество\n"
                        f"✅ Быстрая доставка\n"
                        f"✅ Гарантия 12 месяцев"
                    )
                }

            feat_list = [f.strip() for f in features.split(",") if f.strip()]
            description = await llm.generate_description(product_name, feat_list, marketplace)
            return {"description": description}
        except Exception as e:
            logger.error("Error generating description: %s", e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    # ===== Error handler =====
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    return app


def _product_to_response(product: ProductCard) -> ProductCardResponse:
    """Конвертировать ProductCard в API-ответ."""
    return ProductCardResponse(
        marketplace=product.marketplace,
        article=product.article,
        name=product.name,
        brand=product.brand,
        category=product.category,
        price=float(product.price) if product.price else 0.0,
        old_price=float(product.old_price) if product.old_price else None,
        rating=product.rating,
        reviews_count=product.reviews_count,
        stock=product.stock,
        image_url=product.image_url,
        description=product.description,
        characteristics=product.characteristics,
    )
